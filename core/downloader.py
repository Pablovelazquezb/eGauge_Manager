import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from .processor import procesar_csv_contenido
from database.connection import get_connection

def construir_url_egauge(hostname: str, timestamp: int, paso_segundos: int) -> str:
    """Construye URL usando el formato exacto especificado"""
    return f"https://{hostname}/cgi-bin/egauge-show?E&c&S&s={paso_segundos}&n=1&f={timestamp}&F=data.csv&C&Z=LST6"

def descargar_csv_egauge(url: str) -> str:
    """Descarga CSV desde eGauge y retorna el contenido como string"""
    headers = {
        'Accept': 'text/csv,application/csv',
        'User-Agent': 'eGauge-Streamlit-Client/1.0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200 and len(response.text.strip()) > 0:
            return response.text
        else:
            return None
    except Exception:
        return None

def descargar_cliente_paralelo(hostname: str, tabla_nombre: str, timestamps: list) -> dict:
    """Descarga todos los datos de un cliente en paralelo"""
    resultados = {
        'hostname': hostname,
        'tabla_nombre': tabla_nombre,
        'dataframes': [],
        'errores': 0,
        'total_filas': 0
    }
    
    def descargar_timestamp(timestamp):
        """Descarga un timestamp específico"""
        try:
            url = construir_url_egauge(hostname, timestamp, 3600)
            contenido_csv = descargar_csv_egauge(url)
            
            if contenido_csv is None:
                return None
            
            df = procesar_csv_contenido(contenido_csv)
            return df if df is not None and not df.empty else None
            
        except Exception:
            return None
    
    # Descargar en paralelo usando ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Enviar todas las tareas
        future_to_timestamp = {executor.submit(descargar_timestamp, ts): ts for ts in timestamps}
        
        # Recoger resultados
        for future in as_completed(future_to_timestamp):
            try:
                df = future.result()
                if df is not None:
                    resultados['dataframes'].append(df)
                else:
                    resultados['errores'] += 1
            except Exception:
                resultados['errores'] += 1
    
    return resultados

def crear_tabla(tabla_nombre: str, df: pd.DataFrame) -> bool:
    """Crea tabla si no existe o la actualiza si existe"""
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        
        # Verificar si existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            );
        """, (tabla_nombre,))
        tabla_existe = cur.fetchone()[0]
        
        if not tabla_existe:
            # Crear tabla nueva
            columnas_sql = []
            for col in df.columns:
                if col == 'timestamp':
                    sql_type = "TIMESTAMP"
                elif col == 'tarifa':
                    sql_type = "VARCHAR(20)"
                elif pd.api.types.is_numeric_dtype(df[col]):
                    sql_type = "FLOAT"
                else:
                    sql_type = "TEXT"
                columnas_sql.append(f'"{col}" {sql_type}')
            
            create_sql = f"""
            CREATE TABLE "{tabla_nombre}" (
                id SERIAL PRIMARY KEY,
                {", ".join(columnas_sql)},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cur.execute(create_sql)
            
            # Crear índices
            if 'timestamp' in df.columns:
                cur.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "idx_{tabla_nombre}_timestamp" ON "{tabla_nombre}"("timestamp");')
            if 'tarifa' in df.columns:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{tabla_nombre}_tarifa" ON "{tabla_nombre}"("tarifa");')
            
            conn.commit()
        
        cur.close()
        conn.close()
        return True
        
    except Exception:
        if conn:
            conn.close()
        return False

def insertar_datos(tabla_nombre: str, df: pd.DataFrame) -> int:
    """Inserta datos usando UPSERT"""
    conn = get_connection()
    if not conn:
        return 0
        
    try:
        cur = conn.cursor()
        filas_insertadas = 0
        
        for _, row in df.iterrows():
            valores = [None if pd.isna(val) else val for val in row]
            columnas = ', '.join([f'"{col}"' for col in df.columns])
            placeholders = ', '.join(['%s'] * len(valores))
            
            if 'timestamp' in df.columns:
                # UPSERT con timestamp
                sql = f'''
                INSERT INTO "{tabla_nombre}" ({columnas}) VALUES ({placeholders})
                ON CONFLICT ("timestamp") DO UPDATE SET
                {", ".join([f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col != 'timestamp'])}
                '''
            else:
                # INSERT simple
                sql = f'INSERT INTO "{tabla_nombre}" ({columnas}) VALUES ({placeholders})'
            
            try:
                cur.execute(sql, tuple(valores))
                filas_insertadas += 1
            except Exception:
                continue
        
        conn.commit()
        cur.close()
        conn.close()
        return filas_insertadas
        
    except Exception:
        if conn:
            conn.close()
        return 0

def procesar_cliente_completo(hostname: str, tabla_nombre: str, timestamps: list) -> dict:
    """Procesa un cliente completo: descarga en paralelo + inserta en BD"""
    
    # Descargar datos en paralelo
    resultado = descargar_cliente_paralelo(hostname, tabla_nombre, timestamps)
    
    if not resultado['dataframes']:
        return {
            'tabla': tabla_nombre,
            'filas': 0,
            'errores': resultado['errores'],
            'exito': False
        }
    
    # Crear tabla con el primer DataFrame
    primer_df = resultado['dataframes'][0]
    tabla_creada = crear_tabla(tabla_nombre, primer_df)
    
    if not tabla_creada:
        return {
            'tabla': tabla_nombre,
            'filas': 0,
            'errores': resultado['errores'],
            'exito': False
        }
    
    # Insertar todos los DataFrames
    total_filas = 0
    for df in resultado['dataframes']:
        filas = insertar_datos(tabla_nombre, df)
        total_filas += filas
    
    return {
        'tabla': tabla_nombre,
        'filas': total_filas,
        'errores': resultado['errores'],
        'exito': True
    }