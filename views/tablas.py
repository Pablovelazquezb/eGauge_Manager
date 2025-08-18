import streamlit as st
import pandas as pd
from database.models import obtener_tablas_egauge, eliminar_tabla_egauge

def render_ver_tablas():
    """Renderiza la vista de tablas eGauge"""
    st.header("🗄️ Tablas en PostgreSQL")
    st.markdown("**Visualiza y administra todas las tablas de datos eGauge**")
    
    # Obtener información de tablas
    tabla_info = obtener_tablas_egauge()
    
    if not tabla_info:
        st.info("ℹ️ No se encontraron tablas eGauge en la base de datos")
        st.markdown("""
        **¿Por qué no hay tablas?**
        - Aún no has ejecutado ninguna descarga
        - Las tablas no siguen el patrón 'egauge*'
        - Hay un problema de conexión a la base de datos
        """)
        return
    
    st.success(f"✅ Encontradas {len(tabla_info)} tablas eGauge")
    
    # Mostrar tablas en dataframe
    df_tablas = pd.DataFrame(tabla_info)
    
    # Agregar filtros
    _render_filtros_tablas(df_tablas)
    
    # Mostrar tabla
    st.dataframe(df_tablas, use_container_width=True, hide_index=True)
    
    # Estadísticas generales
    _render_estadisticas_generales(df_tablas)
    
    # Sección para eliminar tablas
    _render_seccion_eliminar_tablas(tabla_info)

def _render_filtros_tablas(df_tablas):
    """Renderiza filtros para las tablas"""
    st.subheader("🔍 Filtros")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro por texto
        filtro_texto = st.text_input(
            "Buscar tabla:",
            placeholder="Escribe nombre de tabla...",
            help="Busca por nombre de tabla"
        )
        
        if filtro_texto:
            df_filtrado = df_tablas[df_tablas['Tabla'].str.contains(filtro_texto, case=False, na=False)]
            st.info(f"📋 Mostrando {len(df_filtrado)} de {len(df_tablas)} tablas")
    
    with col2:
        # Filtro por tamaño
        tamanos_unicos = df_tablas['Tamaño'].unique()
        filtro_tamano = st.selectbox(
            "Filtrar por tamaño:",
            options=["Todos"] + list(tamanos_unicos),
            help="Filtrar por tamaño de tabla"
        )
        
        if filtro_tamano != "Todos":
            df_filtrado = df_tablas[df_tablas['Tamaño'] == filtro_tamano]
            st.info(f"📋 Mostrando {len(df_filtrado)} de {len(df_tablas)} tablas")

def _render_estadisticas_generales(df_tablas):
    """Renderiza estadísticas generales de las tablas"""
    st.subheader("📊 Estadísticas Generales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tablas = len(df_tablas)
        st.metric("📋 Total tablas", total_tablas)
    
    with col2:
        # Calcular total de filas (aproximado)
        total_filas = 0
        for filas_str in df_tablas['Filas']:
            try:
                if filas_str != 'Error':
                    # Remover comas y convertir a entero
                    filas_num = int(filas_str.replace(',', ''))
                    total_filas += filas_num
            except:
                continue
        st.metric("📊 Total filas", f"{total_filas:,}")
    
    with col3:
        # Contar tablas con datos válidos
        tablas_con_datos = sum(1 for filas in df_tablas['Filas'] if filas != 'Error' and filas != '0')
        st.metric("✅ Con datos", tablas_con_datos)
    
    with col4:
        # Contar tablas con errores
        tablas_con_errores = sum(1 for filas in df_tablas['Filas'] if filas == 'Error')
        st.metric("❌ Con errores", tablas_con_errores)

def _render_seccion_eliminar_tablas(tabla_info):
    """Renderiza la sección para eliminar tablas"""
    with st.expander("🗑️ Eliminar Tablas"):
        st.warning("⚠️ **Cuidado**: La eliminación de tablas es permanente")
        
        # Selección de tabla
        nombres_tablas = [info['Tabla'] for info in tabla_info]
        tabla_seleccionada = st.selectbox(
            "Seleccionar tabla para eliminar:",
            options=[""] + nombres_tablas,
            help="Elige la tabla que quieres eliminar"
        )
        
        if tabla_seleccionada:
            # Mostrar información de la tabla seleccionada
            info_tabla = next((info for info in tabla_info if info['Tabla'] == tabla_seleccionada), None)
            
            if info_tabla:
                st.info(f"""
                **📋 Información de la tabla:**
                - **Nombre**: {info_tabla['Tabla']}
                - **Filas**: {info_tabla['Filas']}
                - **Tamaño**: {info_tabla['Tamaño']}
                - **Período**: {info_tabla['Período']}
                """)
            
            # Botones de confirmación
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"🗑️ Eliminar {tabla_seleccionada}", type="secondary"):
                    st.session_state[f"confirm_delete_{tabla_seleccionada}"] = True
            
            with col2:
                if st.session_state.get(f"confirm_delete_{tabla_seleccionada}", False):
                    if st.button("✅ Confirmar eliminación", type="primary"):
                        with st.spinner(f"Eliminando tabla {tabla_seleccionada}..."):
                            if eliminar_tabla_egauge(tabla_seleccionada):
                                st.success(f"✅ Tabla {tabla_seleccionada} eliminada correctamente")
                                # Limpiar estado de confirmación
                                if f"confirm_delete_{tabla_seleccionada}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{tabla_seleccionada}"]
                                st.rerun()
                            else:
                                st.error(f"❌ Error eliminando tabla {tabla_seleccionada}")
        
        # Información adicional
        st.markdown("""
        **💡 Notas importantes:**
        - La eliminación es **permanente** y no se puede deshacer
        - Se eliminan todos los datos y la estructura de la tabla
        - Los índices asociados también se eliminan automáticamente
        - Asegúrate de tener backups si los necesitas
        """)

def render_exportar_tablas():
    """Renderiza opciones para exportar datos de tablas"""
    st.subheader("📤 Exportar Datos")
    
    # Obtener lista de tablas
    tabla_info = obtener_tablas_egauge()
    
    if not tabla_info:
        st.info("ℹ️ No hay tablas disponibles para exportar")
        return
    
    nombres_tablas = [info['Tabla'] for info in tabla_info]
    tabla_exportar = st.selectbox(
        "Seleccionar tabla para exportar:",
        options=[""] + nombres_tablas
    )
    
    if tabla_exportar:
        st.info("🚧 **Funcionalidad en desarrollo**")
        st.markdown("""
        **Próximamente podrás:**
        - Exportar datos a CSV
        - Exportar a Excel
        - Filtrar por rango de fechas
        - Exportar solo ciertas columnas
        """)