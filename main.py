import streamlit as st
from datetime import datetime

# Imports de módulos locales
from database.connection import validate_db_credentials, db
from database.models import crear_tabla_clientes

# Importar vistas
from views.dashboard import render_dashboard
from views.clientes import render_gestion_clientes
from views.descarga import render_descarga_individual
from views.tablas import render_ver_tablas
from views.admin import render_admin_clientes
from views.recibos import render_generador_recibos
from views.generador_recibo_cfe import render_generador_recibo_cfe

def render_sidebar_navigation():
    """Renderiza la navegación en el sidebar para todas las páginas"""
    with st.sidebar:
        st.markdown("### 🏠 Navegación")
        
        if st.button("📊 Dashboard", use_container_width=True, key="nav_dashboard", type="primary" if st.session_state.current_page == 'dashboard' else "secondary"):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        
        st.markdown("### 📊 Gestión de Datos")
        if st.button("👥 Gestión de Clientes", use_container_width=True, key="nav_clientes", type="primary" if st.session_state.current_page == 'clientes' else "secondary"):
            st.session_state.current_page = "clientes"
            st.rerun()
        
        if st.button("📥 Descarga Individual", use_container_width=True, key="nav_descarga", type="primary" if st.session_state.current_page == 'descarga' else "secondary"):
            st.session_state.current_page = "descarga"
            st.rerun()
        
        if st.button("🗄️ Ver Tablas", use_container_width=True, key="nav_tablas", type="primary" if st.session_state.current_page == 'tablas' else "secondary"):
            st.session_state.current_page = "tablas"
            st.rerun()
        
        if st.button("📋 Administrar Clientes", use_container_width=True, key="nav_admin", type="primary" if st.session_state.current_page == 'admin' else "secondary"):
            st.session_state.current_page = "admin"
            st.rerun()
        
        st.markdown("### 💰 Facturación")
        if st.button("🧾 Calculadora CFE", use_container_width=True, key="nav_calculadora", type="primary" if st.session_state.current_page == 'calculadora' else "secondary"):
            st.session_state.current_page = "calculadora"
            st.rerun()
        
        if st.button("📄 Generador Recibos", use_container_width=True, key="nav_recibos", type="primary" if st.session_state.current_page == 'recibos' else "secondary"):
            st.session_state.current_page = "recibos"
            st.rerun()

# Configuración de la página
st.set_page_config(
    page_title="eGauge Data Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Función principal con navegación por páginas"""
    
    # Validar credenciales de base de datos
    validate_db_credentials()
    
    # Crear tabla de clientes si no existe
    crear_tabla_clientes()
    
    # Inicializar página actual en session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    
    # Mostrar navegación en sidebar para todas las páginas
    render_sidebar_navigation()
    
    # Agregar botón de regreso en todas las páginas excepto dashboard
    if st.session_state.current_page != 'dashboard':
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button("← Dashboard", use_container_width=True, type="secondary", key="back_to_dashboard"):
                st.session_state.current_page = 'dashboard'
                st.rerun()
    
    # Router de páginas
    page = st.session_state.current_page
    
    if page == 'dashboard':
        render_dashboard()
    elif page == 'clientes':
        render_gestion_clientes()
    elif page == 'descarga':
        render_descarga_individual()
    elif page == 'tablas':
        render_ver_tablas()
    elif page == 'admin':
        render_admin_clientes()
    elif page == 'calculadora':
        render_generador_recibos()
    elif page == 'recibos':
        render_generador_recibo_cfe()
    else:
        # Página por defecto si hay error
        render_dashboard()

if __name__ == "__main__":
    main()