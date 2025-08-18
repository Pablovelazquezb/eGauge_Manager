import streamlit as st
from datetime import datetime

# Imports de módulos locales
from database.connection import validate_db_credentials, db
from database.models import crear_tabla_clientes
from views.clientes import render_gestion_clientes
from views.descarga import render_descarga_masiva
from views.tablas import render_ver_tablas
from views.admin import render_admin_clientes

# Configuración de la página
st.set_page_config(
    page_title="eGauge Data Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar colapsado por defecto
)

def main():
    """Función principal de la aplicación"""
    
    # Título principal
    st.title("⚡ eGauge Data Manager")
    st.markdown("**Sistema completo de gestión y descarga masiva de medidores eGauge**")
    
    # Validar credenciales de base de datos
    validate_db_credentials()
    
    # Crear tabla de clientes si no existe
    crear_tabla_clientes()
    
    # Mostrar estado de conexión de forma compacta
    mostrar_estado_conexion()
    
    # Crear tabs principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 Gestión de Clientes", 
        "📊 Descarga Masiva", 
        "🗄️ Ver Tablas", 
        "📋 Administrar Clientes"
    ])
    
    # Renderizar cada tab
    with tab1:
        render_gestion_clientes()
    
    with tab2:
        render_descarga_masiva()
    
    with tab3:
        render_ver_tablas()
    
    with tab4:
        render_admin_clientes()
    
    # Footer simplificado
    mostrar_footer()

def mostrar_estado_conexion():
    """Muestra el estado de conexión de forma compacta"""
    col1, col2, col3 = st.columns([2, 3, 1])
    
    with col1:
        if db.test_connection():
            st.success("🗄️ PostgreSQL: Conectado")
        else:
            st.error("🗄️ PostgreSQL: Error")
    
    with col2:
        st.info(f"🔗 {db.get_connection_info()}")
    
    with col3:
        # Espacio para futuros indicadores
        pass

def mostrar_footer():
    """Muestra un footer minimalista"""
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "<b>eGauge Data Manager</b> - Sistema profesional de gestión y descarga masiva"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()