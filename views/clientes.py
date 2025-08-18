import streamlit as st
import pandas as pd
import time as time_module
from database.models import cargar_clientes, guardar_clientes
from core.processor import parsear_lista_clientes, parsear_csv_clientes, limpiar_nombre_tabla, extraer_hostname_desde_url

def render_gestion_clientes():
    """Renderiza la vista de gestión de clientes"""
    st.header("👥 Gestión de Clientes")
    st.markdown("**Agrega y administra tu lista de clientes eGauge**")
    
    # Mostrar clientes actuales
    clientes_actuales = cargar_clientes()
    
    if clientes_actuales:
        st.success(f"✅ Tienes {len(clientes_actuales)} clientes activos registrados")
        
        # Mostrar lista resumida
        with st.expander("👀 Ver clientes actuales"):
            for nombre, hostname, url, tabla, cliente_id in clientes_actuales:
                st.write(f"**{nombre}** → `{tabla}` ({hostname})")
    else:
        st.info("ℹ️ No tienes clientes registrados. ¡Agrega algunos abajo!")
    
    st.subheader("➕ Agregar Nuevos Clientes")
    
    # Método de entrada
    metodo_entrada = st.radio(
        "Método de entrada:",
        ["📝 Texto (Lista)", "📁 Archivo CSV", "🔗 Individual"]
    )
    
    clientes_para_guardar = []
    
    if metodo_entrada == "📝 Texto (Lista)":
        clientes_para_guardar = _render_entrada_texto()
    elif metodo_entrada == "📁 Archivo CSV":
        clientes_para_guardar = _render_entrada_csv()
    elif metodo_entrada == "🔗 Individual":
        clientes_para_guardar = _render_entrada_individual()
    
    # Mostrar preview y guardar
    if clientes_para_guardar:
        _render_preview_y_guardar(clientes_para_guardar)

def _render_entrada_texto():
    """Renderiza entrada por texto"""
    clientes_text = st.text_area(
        "Formato: Nombre | URL (uno por línea)",
        placeholder="""Macro 2 Nave 4 SE 2 | https://egauge86216.egaug.es/63C1A/l/es/classic.html
Dormi | https://egauge90707.egaug.es/64E77/l/es/classic.html
Transformador Novatec | https://egauge52115.egaug.es/5DB9E/l/es/classic.html""",
        height=200
    )
    
    if clientes_text.strip():
        return parsear_lista_clientes(clientes_text)
    return []

def _render_entrada_csv():
    """Renderiza entrada por archivo CSV"""
    archivo_csv = st.file_uploader(
        "Sube archivo CSV con columnas: nombre,url", 
        type=['csv']
    )
    
    if archivo_csv:
        try:
            df_clientes = pd.read_csv(archivo_csv)
            
            if 'nombre' in df_clientes.columns and 'url' in df_clientes.columns:
                clientes = parsear_csv_clientes(df_clientes)
                if clientes:
                    st.success(f"✅ Archivo procesado: {len(clientes)} clientes encontrados")
                return clientes
            else:
                st.error("❌ El CSV debe tener columnas 'nombre' y 'url'")
                return []
        except Exception as e:
            st.error(f"❌ Error procesando CSV: {e}")
            return []
    return []

def _render_entrada_individual():
    """Renderiza entrada individual"""
    col1, col2 = st.columns(2)
    with col1:
        nombre_individual = st.text_input("Nombre del cliente", placeholder="Ej: Macro 2 Nave 4")
    with col2:
        url_individual = st.text_input("URL", placeholder="https://egauge90707.egaug.es/...")
    
    if nombre_individual and url_individual:
        hostname = extraer_hostname_desde_url(url_individual)
        tabla_nombre = limpiar_nombre_tabla(nombre_individual)
        return [(nombre_individual, hostname, url_individual, tabla_nombre)]
    return []

def _render_preview_y_guardar(clientes_para_guardar):
    """Renderiza preview y botón de guardar"""
    st.subheader("👀 Preview de clientes a agregar:")
    
    df_preview = pd.DataFrame(clientes_para_guardar, 
                            columns=['Nombre', 'Hostname', 'URL', 'Tabla'])
    st.dataframe(df_preview, use_container_width=True)
    
    # Verificar duplicados
    nombres_tablas = [tabla for _, _, _, tabla in clientes_para_guardar]
    duplicados = len(nombres_tablas) != len(set(nombres_tablas))
    
    if duplicados:
        st.warning("⚠️ Hay nombres de tabla duplicados. Se sobrescribirán entre sí.")
    
    # Botón para guardar
    if st.button("💾 Guardar Clientes", type="primary"):
        with st.spinner("Guardando clientes..."):
            guardados, actualizados = guardar_clientes(clientes_para_guardar)
            
            if guardados > 0:
                st.success(f"✅ {guardados} clientes nuevos guardados")
            if actualizados > 0:
                st.info(f"🔄 {actualizados} clientes existentes actualizados")
            
            if guardados > 0 or actualizados > 0:
                st.balloons()
                time_module.sleep(2)
                st.rerun()
            else:
                st.warning("⚠️ No se guardaron clientes. Verifica los datos.")