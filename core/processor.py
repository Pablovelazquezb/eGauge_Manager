import pandas as pd
import numpy as np
import io
from datetime import datetime, time, date, timedelta
from urllib.parse import urlparse
import pytz

# ============================================================================
# FUNCIONES ORIGINALES (Mantenidas para compatibilidad)
# ============================================================================

def es_horario_de_verano(fecha):
    """Determina si una fecha está en horario de verano (función original)"""
    año = fecha.year
    primer_domingo_abril = min([date(año, 4, d) for d in range(1, 8) if date(año, 4, d).weekday() == 6])
    ultimo_domingo_octubre = max([date(año, 10, d) for d in range(25, 32) if date(año, 10, d).weekday() == 6])
    return primer_domingo_abril <= fecha.date() < ultimo_domingo_octubre

def clasificar_tarifa(fecha):
    """Clasifica la tarifa eléctrica según la fecha/hora (función original)"""
    hora = fecha.time()
    dia = fecha.weekday()
    verano = es_horario_de_verano(fecha)

    def en(h, inicio, fin): 
        return inicio <= h < fin

    if verano:
        if dia < 5:  # Lunes a Viernes
            if en(hora, time(0, 0), time(6, 0)) or en(hora, time(22, 0), time(23, 59, 59)):
                return "Base"
            elif en(hora, time(6, 0), time(20, 0)):
                return "Intermedio"
            else:
                return "Punta"
        elif dia == 5:  # Sábado
            return "Base" if en(hora, time(0, 0), time(7, 0)) else "Intermedio"
        else:  # Domingo
            return "Base" if en(hora, time(0, 0), time(19, 0)) else "Intermedio"
    else:
        if dia < 5:  # Lunes a Viernes
            if en(hora, time(0, 0), time(6, 0)) or en(hora, time(22, 0), time(23, 59, 59)):
                return "Base"
            elif en(hora, time(6, 0), time(18, 0)):
                return "Intermedio"
            else:
                return "Punta"
        elif dia == 5:  # Sábado
            if en(hora, time(0, 0), time(8, 0)) or en(hora, time(21, 0), time(23, 59, 59)):
                return "Base"
            elif en(hora, time(8, 0), time(19, 0)):
                return "Intermedio"
            else:
                return "Punta"
        else:  # Domingo
            return "Base" if en(hora, time(0, 0), time(18, 0)) else "Intermedio"

# ============================================================================
# FUNCIONES PRINCIPALES (Nueva lógica CFE)
# ============================================================================

def _first_sunday_of_april(year):
    """Calcula el primer domingo de abril para horario de verano CFE"""
    d = datetime(year, 4, 1)
    offset = (6 - d.weekday()) % 7
    return d + timedelta(days=offset)

def _last_sunday_of_october(year):
    """Calcula el último domingo de octubre para horario de verano CFE"""
    d = datetime(year, 10, 31)
    offset = (d.weekday() - 6) % 7
    return d - timedelta(days=offset)

def _is_summer_cfe(dt_local):
    """Determina si una fecha está en horario de verano CFE (versión mejorada)"""
    y = dt_local.year
    start = _first_sunday_of_april(y)
    end = _last_sunday_of_october(y)
    tz = dt_local.tzinfo
    
    if tz is None:
        # Si no hay timezone, asumir que es hora local
        return start.date() <= dt_local.date() < end.date()
    
    start = tz.localize(start.replace(hour=0, minute=0, second=0, microsecond=0))
    end = tz.localize(end.replace(hour=0, minute=0, second=0, microsecond=0))
    return (dt_local >= start) & (dt_local < end)

def classify_gdmth_period(ts_series: pd.Series, tz_name: str = "America/Mexico_City", holidays: set | None = None) -> pd.Series:
    """
    Clasifica períodos tarifarios GDMTH con soporte completo de timezone y días festivos
    
    Args:
        ts_series: Serie de pandas con timestamps
        tz_name: Zona horaria (default: America/Mexico_City)
        holidays: Set de fechas que se consideran festivos (tratados como domingo)
    
    Returns:
        Serie de pandas con clasificaciones: "Base", "Intermedio", "Punta"
    """
    if holidays is None:
        holidays = set()

    try:
        tz = pytz.timezone(tz_name)
    except:
        # Si no se puede cargar la timezone, usar el método original
        return ts_series.apply(clasificar_tarifa)

    # Convertir a datetime si no lo es
    if pd.api.types.is_datetime64_any_dtype(ts_series):
        if ts_series.dt.tz is None:
            s = ts_series.dt.tz_localize(tz, nonexistent="shift_forward", ambiguous="NaT")
        else:
            s = ts_series.dt.tz_convert(tz)
    else:
        s = pd.to_datetime(ts_series, errors="coerce")
        if s.dt.tz is None:
            s = s.dt.tz_localize(tz, nonexistent="shift_forward", ambiguous="NaT")

    # Extraer componentes temporales
    dow = s.dt.weekday  # 0=Monday, 6=Sunday
    hour = s.dt.hour
    minute = s.dt.minute
    mins = hour * 60 + minute
    date_only = s.dt.date
    
    # Determinar días especiales
    is_holiday = date_only.astype("string").isin({str(d) for d in holidays}) | date_only.isin({getattr(d, "date", lambda: d)() for d in holidays})
    is_sunday = (dow == 6)
    is_saturday = (dow == 5)
    is_weekday = (dow <= 4)
    is_festivo_o_domingo = is_holiday | is_sunday

    # Determinar si es horario de verano
    is_summer = s.map(lambda dt: _is_summer_cfe(dt) if pd.notna(dt) else np.nan)

    # Inicializar resultado
    res = pd.Series(index=s.index, dtype="string")

    # ========== REGLAS DE VERANO ==========
    # Lunes a Viernes
    v_wk_base = (mins >= 0) & (mins < 360)  # 00:00-06:00
    v_wk_punta = (mins >= 1200) & (mins < 1320)  # 20:00-22:00
    v_wk_inter_1 = (mins >= 360) & (mins < 1200)  # 06:00-20:00
    v_wk_inter_2 = (mins >= 1320) & (mins < 1440)  # 22:00-24:00

    # Sábado
    v_sat_base = (mins >= 0) & (mins < 420)  # 00:00-07:00
    v_sat_inter = (mins >= 420) & (mins < 1440)  # 07:00-24:00

    # Domingo/Festivos
    v_sun_base = (mins >= 0) & (mins < 1140)  # 00:00-19:00
    v_sun_inter = (mins >= 1140) & (mins < 1440)  # 19:00-24:00

    # ========== REGLAS DE INVIERNO ==========
    # Lunes a Viernes
    i_wk_base = (mins >= 0) & (mins < 360)  # 00:00-06:00
    i_wk_punta = (mins >= 1080) & (mins < 1320)  # 18:00-22:00
    i_wk_inter_1 = (mins >= 360) & (mins < 1080)  # 06:00-18:00
    i_wk_inter_2 = (mins >= 1320) & (mins < 1440)  # 22:00-24:00

    # Sábado
    i_sat_base = (mins >= 0) & (mins < 480)  # 00:00-08:00
    i_sat_punta = (mins >= 1140) & (mins < 1260)  # 19:00-21:00
    i_sat_inter_1 = (mins >= 480) & (mins < 1140)  # 08:00-19:00
    i_sat_inter_2 = (mins >= 1260) & (mins < 1440)  # 21:00-24:00

    # Domingo/Festivos
    i_sun_base = (mins >= 0) & (mins < 1080)  # 00:00-18:00
    i_sun_inter = (mins >= 1080) & (mins < 1440)  # 18:00-24:00

    # ========== APLICAR REGLAS DE VERANO ==========
    mask_v = is_summer.fillna(False)
    
    # Lunes a Viernes - Verano
    res[mask_v & is_weekday & v_wk_base] = "Base"
    res[mask_v & is_weekday & v_wk_punta] = "Punta"
    res[mask_v & is_weekday & (v_wk_inter_1 | v_wk_inter_2)] = "Intermedio"

    # Sábado - Verano
    res[mask_v & is_saturday & v_sat_base] = "Base"
    res[mask_v & is_saturday & v_sat_inter] = "Intermedio"

    # Domingo/Festivos - Verano
    res[mask_v & is_festivo_o_domingo & v_sun_base] = "Base"
    res[mask_v & is_festivo_o_domingo & v_sun_inter] = "Intermedio"

    # ========== APLICAR REGLAS DE INVIERNO ==========
    mask_i = (~is_summer.fillna(False))
    
    # Lunes a Viernes - Invierno
    res[mask_i & is_weekday & i_wk_base] = "Base"
    res[mask_i & is_weekday & i_wk_punta] = "Punta"
    res[mask_i & is_weekday & (i_wk_inter_1 | i_wk_inter_2)] = "Intermedio"

    # Sábado - Invierno
    res[mask_i & is_saturday & i_sat_base] = "Base"
    res[mask_i & is_saturday & i_sat_punta] = "Punta"
    res[mask_i & is_saturday & (i_sat_inter_1 | i_sat_inter_2)] = "Intermedio"

    # Domingo/Festivos - Invierno
    res[mask_i & is_festivo_o_domingo & i_sun_base] = "Base"
    res[mask_i & is_festivo_o_domingo & i_sun_inter] = "Intermedio"

    return res

def clasificar_tarifa_mejorada(fecha, timezone_name="America/Mexico_City", holidays=None):
    """
    Versión mejorada de clasificar_tarifa individual con soporte de timezone
    
    Args:
        fecha: datetime object
        timezone_name: Zona horaria
        holidays: Set de fechas festivas
    
    Returns:
        str: "Base", "Intermedio", o "Punta"
    """
    if holidays is None:
        holidays = set()
    
    # Convertir a Serie para usar la función vectorizada
    serie = pd.Series([fecha])
    resultado = classify_gdmth_period(serie, timezone_name, holidays)
    return resultado.iloc[0] if len(resultado) > 0 else clasificar_tarifa(fecha)

# ============================================================================
# FUNCIONES ORIGINALES DE PROCESAMIENTO (Actualizadas)
# ============================================================================

def procesar_csv_contenido(contenido_csv: str, usar_clasificacion_mejorada: bool = True, timezone_name: str = "America/Mexico_City", holidays: set = None) -> pd.DataFrame:
    """
    Procesa contenido CSV y retorna DataFrame con clasificación de tarifas
    
    Args:
        contenido_csv: String con contenido del CSV
        usar_clasificacion_mejorada: Si usar la nueva lógica (True) o la original (False)
        timezone_name: Zona horaria para la clasificación
        holidays: Set de días festivos
    
    Returns:
        DataFrame procesado con columna 'tarifa'
    """
    try:
        # Detectar separador
        primera_linea = contenido_csv.split('\n')[0]
        separador = ',' if ',' in primera_linea else ';'
        
        # Leer CSV
        df = pd.read_csv(io.StringIO(contenido_csv), sep=separador)
        
        if df.empty:
            return None
        
        # Limpiar nombres de columnas
        nuevas_columnas = []
        for i, col in enumerate(df.columns):
            col_str = str(col).strip()
            
            # Primera columna = timestamp
            if i == 0:
                col_str = 'timestamp'
            elif col_str.isdigit() or col_str.startswith('Unnamed'):
                col_str = f'sensor_{i}'
            
            # Limpiar caracteres problemáticos
            for old, new in {" ": "_", "%": "pct", "+": "plus", "-": "_", ".": "_"}.items():
                col_str = col_str.replace(old, new)
            
            nuevas_columnas.append(col_str)
        
        df.columns = nuevas_columnas
        
        # Procesar timestamp
        if 'timestamp' in df.columns:
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                
                # Clasificar tarifas
                if df['timestamp'].notna().any():
                    if usar_clasificacion_mejorada:
                        # Usar nueva lógica mejorada
                        try:
                            df['tarifa'] = classify_gdmth_period(df['timestamp'], timezone_name, holidays)
                        except Exception as e:
                            # Fallback a método original si hay error
                            print(f"Warning: Error en clasificación mejorada, usando método original: {e}")
                            df['tarifa'] = df['timestamp'].apply(clasificar_tarifa)
                    else:
                        # Usar lógica original
                        df['tarifa'] = df['timestamp'].apply(clasificar_tarifa)
                
            except Exception:
                pass
        
        # Convertir columnas numéricas
        for col in df.columns:
            if col not in ['timestamp', 'tarifa']:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except:
                    pass
        
        return df
        
    except Exception:
        return None

# ============================================================================
# FUNCIONES AUXILIARES (Sin cambios)
# ============================================================================

def extraer_hostname_desde_url(url: str) -> str:
    """Extrae el hostname desde una URL completa"""
    if url.startswith("http"):
        return urlparse(url).netloc
    else:
        return url.strip()

def limpiar_nombre_tabla(nombre: str) -> str:
    """Convierte un nombre de cliente en nombre de tabla válido"""
    tabla_nombre = nombre.lower().replace(' ', '_')
    
    # Limpiar caracteres especiales
    for char in ['-', '.', '(', ')', '[', ']', '&', '@', '#', '$', '%', '^', '*', '+', '=', '|']:
        tabla_nombre = tabla_nombre.replace(char, '_')
    
    # Eliminar múltiples guiones bajos
    while '__' in tabla_nombre:
        tabla_nombre = tabla_nombre.replace('__', '_')
    
    tabla_nombre = tabla_nombre.strip('_')
    
    # Asegurar que no esté vacío
    if not tabla_nombre:
        tabla_nombre = "cliente_sin_nombre"
    
    return tabla_nombre

def parsear_lista_clientes(texto: str) -> list:
    """Parsea texto con formato 'Nombre | URL' y retorna lista de clientes"""
    clientes = []
    
    if not texto.strip():
        return clientes
    
    for linea in texto.strip().split('\n'):
        if '|' in linea:
            try:
                nombre, url = linea.split('|', 1)
                nombre = nombre.strip()
                url = url.strip()
                
                if nombre and url:
                    hostname = extraer_hostname_desde_url(url)
                    tabla_nombre = limpiar_nombre_tabla(nombre)
                    
                    clientes.append((nombre, hostname, url, tabla_nombre))
                    
            except Exception:
                continue
    
    return clientes

def parsear_csv_clientes(df_csv: pd.DataFrame) -> list:
    """Parsea DataFrame de CSV y retorna lista de clientes"""
    clientes = []
    
    if 'nombre' not in df_csv.columns or 'url' not in df_csv.columns:
        return clientes
    
    for _, row in df_csv.iterrows():
        try:
            nombre = str(row['nombre']).strip()
            url = str(row['url']).strip()
            
            if nombre and url and nombre != 'nan' and url != 'nan':
                hostname = extraer_hostname_desde_url(url)
                tabla_nombre = limpiar_nombre_tabla(nombre)
                
                clientes.append((nombre, hostname, url, tabla_nombre))
                
        except Exception:
            continue
    
    return clientes

def generar_timestamps_rango(datetime_inicio: datetime, datetime_fin: datetime, paso_segundos: int) -> list:
    """Genera lista de timestamps epoch para el rango especificado"""
    timestamps = []
    timestamp_actual = int(datetime_inicio.timestamp())
    timestamp_final = int(datetime_fin.timestamp())
    
    while timestamp_actual <= timestamp_final:
        timestamps.append(timestamp_actual)
        timestamp_actual += paso_segundos
    
    return timestamps

# ============================================================================
# FUNCIONES DE CONFIGURACIÓN Y UTILIDADES
# ============================================================================

def set_default_timezone(timezone_name: str = "America/Mexico_City"):
    """Establece la zona horaria por defecto para el sistema"""
    global DEFAULT_TIMEZONE
    DEFAULT_TIMEZONE = timezone_name

def get_cfe_holidays(year: int) -> set:
    """
    Retorna días festivos CFE para un año específico
    Puedes expandir esta función con los días festivos oficiales
    """
    holidays = set()
    
    # Días festivos fijos
    holidays.add(date(year, 1, 1))   # Año Nuevo
    holidays.add(date(year, 5, 1))   # Día del Trabajo
    holidays.add(date(year, 9, 16))  # Independencia
    holidays.add(date(year, 12, 25)) # Navidad
    
    # Agregar más días festivos según necesidad
    # holidays.add(date(year, 11, 20))  # Revolución Mexicana
    # holidays.add(date(year, 12, 12))  # Virgen de Guadalupe
    
    return holidays

# Variable global para timezone por defecto
DEFAULT_TIMEZONE = "America/Mexico_City"