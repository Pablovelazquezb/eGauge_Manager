import streamlit as st
import pandas as pd
from .connection import get_connection

def crear_tabla_clientes():
    """Crea tabla para guardar la lista de clientes"""
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS egauge_clientes (
                id SERIAL PRIMARY KEY,
                nombre_cliente VARCHAR(255) NOT NULL,
                hostname VARCHAR(255) NOT NULL,
                url_completa TEXT,
                tabla_nombre VARCHAR(255) NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tabla_nombre)
            );
        """)
        
        # Crear índices
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_egauge_clientes_activo ON egauge_clientes(activo);
            CREATE INDEX IF NOT EXISTS idx_egauge_clientes_hostname ON egauge_clientes(hostname);
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creando tabla de clientes: {e}")
        if conn:
            conn.close()
        return False

def guardar_clientes(clientes_lista_completa):
    """Guarda la lista de clientes en la base de datos"""
    conn = get_connection()
    if not conn:
        return 0, 0
        
    try:
        cur = conn.cursor()
        
        clientes_guardados = 0
        clientes_actualizados = 0
        
        for nombre_cliente, hostname, url_completa, tabla_nombre in clientes_lista_completa:
            try:
                cur.execute("""
                    INSERT INTO egauge_clientes (nombre_cliente, hostname, url_completa, tabla_nombre)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (tabla_nombre) 
                    DO UPDATE SET 
                        nombre_cliente = EXCLUDED.nombre_cliente,
                        hostname = EXCLUDED.hostname,
                        url_completa = EXCLUDED.url_completa,
                        updated_at = CURRENT_TIMESTAMP,
                        activo = TRUE
                """, (nombre_cliente, hostname, url_completa, tabla_nombre))
                
                if cur.rowcount == 1:
                    clientes_guardados += 1
                else:
                    clientes_actualizados += 1
                    
            except Exception as e:
                st.warning(f"Error guardando cliente {nombre_cliente}: {e}")
                continue
        
        conn.commit()
        cur.close()
        conn.close()
        
        return clientes_guardados, clientes_actualizados
        
    except Exception as e:
        st.error(f"Error en guardar_clientes: {e}")
        if conn:
            conn.close()
        return 0, 0

def cargar_clientes(solo_activos=True):
    """Carga la lista de clientes desde la base de datos"""
    conn = get_connection()
    if not conn:
        return []
        
    try:
        cur = conn.cursor()
        
        if solo_activos:
            cur.execute("""
                SELECT nombre_cliente, hostname, url_completa, tabla_nombre, id
                FROM egauge_clientes 
                WHERE activo = TRUE
                ORDER BY nombre_cliente
            """)
        else:
            cur.execute("""
                SELECT nombre_cliente, hostname, url_completa, tabla_nombre, id, activo
                FROM egauge_clientes 
                ORDER BY nombre_cliente
            """)
        
        clientes = cur.fetchall()
        cur.close()
        conn.close()
        return clientes
        
    except Exception as e:
        st.error(f"Error cargando clientes: {e}")
        if conn:
            conn.close()
        return []

def toggle_cliente_activo(cliente_id, activo):
    """Activa o desactiva un cliente"""
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE egauge_clientes 
            SET activo = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (activo, cliente_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando cliente: {e}")
        if conn:
            conn.close()
        return False

def eliminar_cliente(cliente_id):
    """Elimina un cliente permanentemente"""
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM egauge_clientes WHERE id = %s", (cliente_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error eliminando cliente: {e}")
        if conn:
            conn.close()
        return False

def obtener_tablas_egauge():
    """Obtiene información de todas las tablas eGauge"""
    conn = get_connection()
    if not conn:
        return []
        
    try:
        cur = conn.cursor()
        
        # Obtener tablas básicas
        cur.execute("""
            SELECT table_name, 
                   pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'egauge%'
            ORDER BY table_name;
        """)
        
        tablas = cur.fetchall()
        
        if not tablas:
            cur.close()
            conn.close()
            return []
        
        # Agregar información adicional
        tabla_info = []
        for tabla_nombre, size in tablas:
            try:
                # Contar filas
                cur.execute(f'SELECT COUNT(*) FROM "{tabla_nombre}";')
                filas = cur.fetchone()[0]
                
                # Obtener rango de fechas
                try:
                    cur.execute(f'SELECT MIN("timestamp"), MAX("timestamp") FROM "{tabla_nombre}" WHERE "timestamp" IS NOT NULL;')
                    min_fecha, max_fecha = cur.fetchone()
                    if min_fecha and max_fecha:
                        rango = f"{min_fecha.strftime('%Y-%m-%d')} → {max_fecha.strftime('%Y-%m-%d')}"
                    else:
                        rango = "Sin fechas"
                except:
                    rango = "Sin timestamp"
                
                tabla_info.append({
                    'Tabla': tabla_nombre,
                    'Filas': f"{filas:,}",
                    'Tamaño': size,
                    'Período': rango
                })
            except:
                tabla_info.append({
                    'Tabla': tabla_nombre,
                    'Filas': 'Error',
                    'Tamaño': size,
                    'Período': 'Error'
                })
        
        cur.close()
        conn.close()
        return tabla_info
        
    except Exception as e:
        st.error(f"Error obteniendo tablas: {e}")
        if conn:
            conn.close()
        return []

def eliminar_tabla_egauge(tabla_nombre):
    """Elimina una tabla eGauge específica"""
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        cur.execute(f'DROP TABLE IF EXISTS "{tabla_nombre}" CASCADE;')
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error eliminando tabla {tabla_nombre}: {e}")
        if conn:
            conn.close()
        return False

def ejecutar_acciones_masivas_clientes(accion):
    """Ejecuta acciones masivas en clientes"""
    conn = get_connection()
    if not conn:
        return False, 0
        
    try:
        cur = conn.cursor()
        
        if accion == "activar_todos":
            cur.execute("UPDATE egauge_clientes SET activo = TRUE")
        elif accion == "desactivar_todos":
            cur.execute("UPDATE egauge_clientes SET activo = FALSE")
        elif accion == "eliminar_inactivos":
            cur.execute("DELETE FROM egauge_clientes WHERE activo = FALSE")
        
        afectados = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return True, afectados
        
    except Exception as e:
        st.error(f"Error en acción masiva: {e}")
        if conn:
            conn.close()
        return False, 0