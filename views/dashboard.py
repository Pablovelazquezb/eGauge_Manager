import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.models import cargar_clientes, obtener_tablas_egauge
from database.connection import db

def render_dashboard():
    """Dashboard principal con vista de clientes"""
    
    # Header principal
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #0b7a4b; margin: 0;">⚡ eGauge Data Manager</h1>
        <p style="font-size: 18px; color: #666; margin: 10px 0;">Dashboard Principal</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Estadísticas generales
    _mostrar_estadisticas_generales()
    
    st.divider()
    
    # Vista de clientes
    _mostrar_vista_clientes()

def _mostrar_estadisticas_generales():
    """Muestra estadísticas generales del sistema"""
    
    # Obtener datos
    clientes = cargar_clientes()
    tablas = obtener_tablas_egauge()
    
    # Estado de conexión
    conexion_ok = db.test_connection()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🔗 Estado PostgreSQL",
            value="Conectado" if conexion_ok else "Error",
            delta="Operativo" if conexion_ok else "Revisar conexión"
        )
    
    with col2:
        st.metric(
            label="👥 Clientes Activos",
            value=len(clientes),
            delta=f"{len([c for c in clientes if len(c) > 4])} registrados" if clientes else "0 registrados"
        )
    
    with col3:
        st.metric(
            label="🗄️ Tablas de Datos",
            value=len(tablas),
            delta="Con datos" if tablas else "Sin datos"
        )
    
    with col4:
        total_registros = 0
        if tablas:
            for tabla in tablas:
                try:
                    filas_str = tabla.get('Filas', '0')
                    if filas_str != 'Error':
                        filas = int(filas_str.replace(',', ''))
                        total_registros += filas
                except:
                    continue
        
        st.metric(
            label="📊 Total Registros",
            value=f"{total_registros:,}",
            delta="Datos procesados"
        )

def _mostrar_vista_clientes():
    """Muestra la vista principal de clientes"""
    
    st.subheader("👥 Vista de Clientes")
    
    clientes = cargar_clientes()
    
    if not clientes:
        st.info("No hay clientes registrados")
        st.markdown("### 🚀 Primeros pasos:")
        st.markdown("1. **Gestión de Clientes**: Agrega tus medidores eGauge")
        st.markdown("2. **Descarga Individual**: Obtén datos de consumo")
        st.markdown("3. **Calculadora CFE**: Calcula costos eléctricos")
        st.markdown("4. **Generador Recibos**: Crea recibos profesionales")
        return
    
    # Filtros
    col1, col2 = st.columns([2, 1])
    with col1:
        buscar = st.text_input("🔍 Buscar cliente", placeholder="Escribe nombre o hostname...")
    with col2:
        mostrar_todos = st.checkbox("Mostrar todos los detalles", value=False)
    
    # Filtrar clientes
    clientes_filtrados = clientes
    if buscar:
        clientes_filtrados = [
            c for c in clientes 
            if buscar.lower() in c[0].lower() or buscar.lower() in c[1].lower()
        ]
    
    st.write(f"**Mostrando {len(clientes_filtrados)} de {len(clientes)} clientes**")
    
    # Mostrar clientes en cards
    if mostrar_todos:
        _mostrar_clientes_detallado(clientes_filtrados)
    else:
        _mostrar_clientes_grid(clientes_filtrados)

def _mostrar_clientes_grid(clientes):
    """Muestra clientes en formato grid compacto"""
    
    # Organizar en filas de 3 columnas
    for i in range(0, len(clientes), 3):
        cols = st.columns(3)
        
        for j, col in enumerate(cols):
            if i + j < len(clientes):
                cliente = clientes[i + j]
                nombre, hostname, url, tabla, cliente_id = cliente
                
                with col:
                    # Card del cliente
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #ddd; 
                        border-radius: 8px; 
                        padding: 15px; 
                        margin: 10px 0;
                        background: white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <div style="font-weight: bold; color: #0b7a4b; margin-bottom: 8px;">
                            {nombre}
                        </div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                            🔗 {hostname}
                        </div>
                        <div style="font-size: 12px; color: #666;">
                            📊 {tabla}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botones de acción
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("📥", key=f"desc_{cliente_id}", help="Descargar datos"):
                            st.session_state.current_page = "descarga"
                            st.session_state.cliente_seleccionado = nombre
                            st.rerun()
                    with col_btn2:
                        if st.button("🧾", key=f"calc_{cliente_id}", help="Calcular CFE"):
                            st.session_state.current_page = "calculadora"
                            st.session_state.cliente_seleccionado = nombre
                            st.rerun()

def _mostrar_clientes_detallado(clientes):
    """Muestra clientes en formato detallado con tabla"""
    
    # Crear DataFrame para mostrar
    datos_clientes = []
    for nombre, hostname, url, tabla, cliente_id in clientes:
        datos_clientes.append({
            'Cliente': nombre,
            'Hostname': hostname,
            'Tabla': tabla,
            'URL': url if url else "N/A"
        })
    
    if datos_clientes:
        df_clientes = pd.DataFrame(datos_clientes)
        st.dataframe(df_clientes, use_container_width=True, hide_index=True)
        
        # Acciones masivas
        st.subheader("⚡ Acciones Rápidas")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Ir a Descargas", use_container_width=True):
                st.session_state.current_page = "descarga"
                st.rerun()
        
        with col2:
            if st.button("🧾 Ir a Calculadora", use_container_width=True):
                st.session_state.current_page = "calculadora"
                st.rerun()
        
        with col3:
            if st.button("📋 Administrar", use_container_width=True):
                st.session_state.current_page = "admin"
                st.rerun()
    
    # Información adicional
    st.markdown("### 💡 Información")
    st.info("""
    **Próximos pasos sugeridos:**
    - 📥 **Descargar datos** de medidores para análisis
    - 🧾 **Calcular costos** CFE por cliente
    - 📄 **Generar recibos** profesionales
    - 📋 **Administrar** clientes activos/inactivos
    """)