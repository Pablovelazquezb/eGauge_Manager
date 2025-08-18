import streamlit as st
from database.models import (
    cargar_clientes, toggle_cliente_activo, eliminar_cliente, 
    ejecutar_acciones_masivas_clientes
)

def render_admin_clientes():
    """Renderiza la vista de administración de clientes"""
    st.header("📋 Administrar Clientes")
    st.markdown("**Gestiona tu lista completa de clientes eGauge**")
    
    # Cargar todos los clientes (activos e inactivos)
    todos_clientes = cargar_clientes(solo_activos=False)
    
    if not todos_clientes:
        st.info("ℹ️ No tienes clientes registrados aún")
        return
    
    # Mostrar estadísticas
    _mostrar_estadisticas_clientes(todos_clientes)
    
    # Filtros
    clientes_filtrados = _aplicar_filtros_clientes(todos_clientes)
    
    if not clientes_filtrados:
        st.info("ℹ️ No se encontraron clientes con los filtros aplicados")
        return
    
    # Mostrar clientes
    _mostrar_lista_clientes(clientes_filtrados)
    
    # Acciones masivas
    _mostrar_acciones_masivas()

def _mostrar_estadisticas_clientes(todos_clientes):
    """Muestra estadísticas generales de clientes"""
    activos = sum(1 for cliente in todos_clientes if cliente[5])  # cliente[5] es 'activo'
    inactivos = len(todos_clientes) - activos
    
    st.success(f"📊 Total de clientes registrados: {len(todos_clientes)}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Activos", activos)
    with col2:
        st.metric("❌ Inactivos", inactivos)
    with col3:
        porcentaje_activos = (activos / len(todos_clientes)) * 100 if todos_clientes else 0
        st.metric("📈 % Activos", f"{porcentaje_activos:.1f}%")

def _aplicar_filtros_clientes(todos_clientes):
    """Aplica filtros a la lista de clientes"""
    st.subheader("🔍 Filtros")
    
    col1, col2 = st.columns(2)
    with col1:
        filtro_estado = st.selectbox("Filtrar por estado:", ["Todos", "Solo activos", "Solo inactivos"])
    with col2:
        buscar_texto = st.text_input("🔍 Buscar cliente:", placeholder="Escribe nombre o hostname...")
    
    # Aplicar filtros
    clientes_filtrados = []
    for cliente in todos_clientes:
        nombre, hostname, url, tabla, cliente_id, activo = cliente
        
        # Filtro por estado
        if filtro_estado == "Solo activos" and not activo:
            continue
        elif filtro_estado == "Solo inactivos" and activo:
            continue
        
        # Filtro por búsqueda
        if buscar_texto and buscar_texto.lower() not in nombre.lower() and buscar_texto.lower() not in hostname.lower():
            continue
        
        clientes_filtrados.append(cliente)
    
    if clientes_filtrados:
        st.info(f"📋 Mostrando {len(clientes_filtrados)} clientes")
    
    return clientes_filtrados

def _mostrar_lista_clientes(clientes_filtrados):
    """Muestra la lista de clientes con opciones de administración"""
    st.subheader("👥 Lista de Clientes")
    
    for cliente in clientes_filtrados:
        _mostrar_cliente_individual(cliente)

def _mostrar_cliente_individual(cliente):
    """Muestra un cliente individual con sus opciones"""
    nombre, hostname, url, tabla, cliente_id, activo = cliente
    
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
        
        with col1:
            status_icon = "✅" if activo else "❌"
            st.write(f"{status_icon} **{nombre}**")
            st.caption(f"Tabla: `{tabla}`")
        
        with col2:
            st.write(f"`{hostname}`")
        
        with col3:
            if url:
                st.link_button("🔗 Ver", url, use_container_width=True)
            else:
                st.write("—")
        
        with col4:
            if activo:
                if st.button("⏸️", key=f"pause_{cliente_id}", help="Desactivar"):
                    if toggle_cliente_activo(cliente_id, False):
                        st.success("Cliente desactivado")
                        st.rerun()
            else:
                if st.button("▶️", key=f"play_{cliente_id}", help="Activar"):
                    if toggle_cliente_activo(cliente_id, True):
                        st.success("Cliente activado")
                        st.rerun()
        
        with col5:
            if st.button("🗑️", key=f"delete_{cliente_id}", help="Eliminar"):
                _manejar_eliminacion_cliente(cliente_id, nombre)
        
        st.divider()

def _manejar_eliminacion_cliente(cliente_id, nombre_cliente):
    """Maneja el proceso de eliminación de un cliente"""
    confirm_key = f"confirm_delete_{cliente_id}"
    
    if st.session_state.get(confirm_key, False):
        # Ejecutar eliminación
        if eliminar_cliente(cliente_id):
            st.success(f"✅ Cliente {nombre_cliente} eliminado")
            # Limpiar estado de confirmación
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]
            st.rerun()
        else:
            st.error(f"❌ Error eliminando cliente {nombre_cliente}")
    else:
        # Solicitar confirmación
        st.session_state[confirm_key] = True
        st.warning(f"⚠️ Haz clic de nuevo para confirmar eliminación de **{nombre_cliente}**")
        st.rerun()

def _mostrar_acciones_masivas():
    """Muestra opciones de acciones masivas"""
    st.subheader("🔧 Acciones Masivas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Activar todos", use_container_width=True):
            _ejecutar_accion_masiva("activar_todos", "activados")
    
    with col2:
        if st.button("❌ Desactivar todos", use_container_width=True):
            _ejecutar_accion_masiva("desactivar_todos", "desactivados")
    
    with col3:
        if st.button("🗑️ Eliminar inactivos", use_container_width=True):
            _confirmar_eliminar_inactivos()

def _ejecutar_accion_masiva(accion, descripcion):
    """Ejecuta una acción masiva en clientes"""
    exito, afectados = ejecutar_acciones_masivas_clientes(accion)
    
    if exito:
        st.success(f"✅ {afectados} clientes {descripcion}")
        st.rerun()
    else:
        st.error(f"❌ Error ejecutando acción masiva")

def _confirmar_eliminar_inactivos():
    """Confirma y ejecuta eliminación de clientes inactivos"""
    confirm_key = "confirm_delete_inactivos"
    
    if st.session_state.get(confirm_key, False):
        # Ejecutar eliminación
        exito, eliminados = ejecutar_acciones_masivas_clientes("eliminar_inactivos")
        
        if exito:
            st.success(f"✅ {eliminados} clientes inactivos eliminados")
            # Limpiar estado de confirmación
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]
            st.rerun()
        else:
            st.error("❌ Error eliminando clientes inactivos")
    else:
        # Solicitar confirmación
        st.session_state[confirm_key] = True
        st.warning("⚠️ Haz clic de nuevo para confirmar eliminación de TODOS los clientes inactivos")
        st.rerun()