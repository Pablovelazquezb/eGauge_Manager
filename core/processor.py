import pandas as pd
import numpy as np
import io
from datetime import datetime, time, date
from urllib.parse import urlparse

def es_horario_de_verano(fecha):
    """Determina si una fecha está en horario de verano"""
    año = fecha.year
    primer_domingo_abril = min([date(año, 4, d) for d in range(1, 8) if date(año, 4, d).weekday() == 6])
    ultimo_domingo_octubre = max([date(año, 10, d) for d in range(25, 32) if date(año, 10, d).weekday() == 6])
    return primer_domingo_abril <= fecha.date() < ultimo_domingo_octubre

def clasificar_tarifa(fecha):
    """Clasifica la tarifa eléctrica según la fecha/hora"""
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

def procesar_csv_contenido(contenido_csv: str) -> pd.DataFrame:
    """Procesa contenido CSV y retorna DataFrame"""
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