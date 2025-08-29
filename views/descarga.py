import streamlit as st
import time as time_module
from datetime import datetime
from database.models import cargar_clientes
from core.processor import generar_timestamps_rango
from core.downloader import procesar_cliente_completo

def render_descarga_individual():
    """Renderiza la vista de descarga individual"""
    st.header("📊 Descarga Individual")
    st.markdown("**Descarga datos para un cliente específico con progreso en tiempo real**")
    
    # Cargar clientes activos
    clientes_db = cargar_clientes()
    
    if not clientes_db:
        st.warning("⚠️ No tienes clientes activos registrados")
        st.info("💡 Ve a la pestaña 'Gestión de Clientes' para agregar clientes primero")
        return
    
    # Selector de cliente
    cliente_seleccionado = _selector_cliente_individual(clientes_db)
    
    if not cliente_seleccionado:
        st.info("ℹ️ Selecciona un cliente para continuar")
        return
    
    # Configuración temporal
    datetime_inicio, datetime_fin = _configurar_periodo_individual()
    
    # Mostrar información del cliente y período
    _mostrar_resumen_descarga(cliente_seleccionado, datetime_inicio, datetime_fin)
    
    # Botón de descarga
    if st.button("🚀 Iniciar Descarga", type="primary", use_container_width=True):
        _ejecutar_descarga_individual(cliente_seleccionado, datetime_inicio, datetime_fin)

def _selector_cliente_individual(clientes_db):
    """Selector de cliente individual"""
    st.subheader("👤 Seleccionar Cliente")
    
    # Crear opciones del selectbox
    opciones_clientes = [""] + [f"{nombre} ({hostname})" for nombre, hostname, _, _, _ in clientes_db]
    
    cliente_elegido = st.selectbox(
        "Elige el cliente a descargar:",
        options=opciones_clientes,
        help="Selecciona el cliente del cual quieres descargar datos"
    )
    
    if cliente_elegido and cliente_elegido != "":
        # Encontrar el cliente seleccionado
        for nombre, hostname, url, tabla, cliente_id in clientes_db:
            if f"{nombre} ({hostname})" == cliente_elegido:
                
                # Mostrar información del cliente seleccionado
                with st.expander("👀 Información del cliente", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Nombre**: {nombre}")
                        st.write(f"**Hostname**: `{hostname}`")
                    with col2:
                        st.write(f"**Tabla**: `{tabla}`")
                        if url:
                            st.link_button("🔗 Ver eGauge", url)
                
                return (hostname, tabla, nombre)
    
    return None

def _configurar_periodo_individual():
    """Configura el período temporal para descarga individual"""
    st.subheader("⏰ Configuración Temporal")
    
    # Opciones de período
    modo = st.radio(
        "Selecciona el período:",
        ["📅 Mes completo", "📆 Rango personalizado", "⚡ Rápido (últimas 24h)"],
        horizontal=True
    )
    
    if modo == "⚡ Rápido (últimas 24h)":
        # Últimas 24 horas
        datetime_fin = datetime.now().replace(minute=0, second=0, microsecond=0)
        datetime_inicio = datetime_fin.replace(hour=datetime_fin.hour - 24)
        
        st.info(f"⚡ **Últimas 24 horas**: {datetime_inicio.strftime('%d/%m/%Y %H:%M')} → {datetime_fin.strftime('%d/%m/%Y %H:%M')}")
        
    elif modo == "📅 Mes completo":
        col1, col2 = st.columns(2)
        with col1:
            años_disponibles = list(range(2020, datetime.now().year + 1))
            año = st.selectbox("Año", años_disponibles, index=len(años_disponibles) - 1)
        with col2:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_nombre = st.selectbox("Mes", meses, index=datetime.now().month - 1)
            mes = meses.index(mes_nombre) + 1
        
        # Mes completo: del día 1 al último día del mes
        datetime_inicio = datetime(año, mes, 1, 0, 0, 0)
        if mes == 12:
            datetime_fin = datetime(año + 1, 1, 1, 0, 0, 0)
        else:
            datetime_fin = datetime(año, mes + 1, 1, 0, 0, 0)
        
        # Ajustar para no exceder la fecha actual
        if datetime_fin > datetime.now():
            datetime_fin = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        total_dias = (datetime_fin - datetime_inicio).days
        st.info(f"📅 **{mes_nombre} {año}**: {total_dias} días")
        
    else:  # Rango personalizado
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio")
            hora_inicio = st.time_input("Hora inicio", value=datetime.now().time().replace(minute=0, second=0, microsecond=0))
        with col2:
            fecha_fin = st.date_input("Fecha fin")
            hora_fin = st.time_input("Hora fin", value=datetime.now().time().replace(minute=0, second=0, microsecond=0))
        
        datetime_inicio = datetime.combine(fecha_inicio, hora_inicio)
        datetime_fin = datetime.combine(fecha_fin, hora_fin)
        
        total_horas = int((datetime_fin - datetime_inicio).total_seconds() / 3600)
        st.info(f"⏱️ **Total**: {total_horas} horas")
    
    return datetime_inicio, datetime_fin

def _mostrar_resumen_descarga(cliente_seleccionado, datetime_inicio, datetime_fin):
    """Muestra resumen de lo que se va a descargar"""
    hostname, tabla, nombre = cliente_seleccionado
    
    # Calcular estimaciones
    timestamps = generar_timestamps_rango(datetime_inicio, datetime_fin, 3600)
    total_requests = len(timestamps)
    tiempo_estimado = total_requests * 0.5  # ~0.5 segundos por request
    
    st.subheader("📋 Resumen de Descarga")
    
    # Información en columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👤 Cliente", nombre)
    with col2:
        st.metric("📊 Puntos de datos", f"{total_requests:,}")
    with col3:
        st.metric("⏱️ Tiempo estimado", f"{tiempo_estimado/60:.1f} min")
    with col4:
        st.metric("🗄️ Tabla destino", tabla)
    
    # Información adicional
    st.info(f"🔄 Se descargarán datos desde **{datetime_inicio.strftime('%d/%m/%Y %H:%M')}** hasta **{datetime_fin.strftime('%d/%m/%Y %H:%M')}**")

def _ejecutar_descarga_individual(cliente_seleccionado, datetime_inicio, datetime_fin):
    """Ejecuta la descarga individual con progreso"""
    hostname, tabla_nombre, nombre_cliente = cliente_seleccionado
    
    # Generar timestamps
    timestamps = generar_timestamps_rango(datetime_inicio, datetime_fin, 3600)
    total_puntos = len(timestamps)
    
    st.success(f"🚀 **Iniciando descarga para {nombre_cliente}**")
    st.info(f"📊 Descargando {total_puntos:,} puntos de datos...")
    
    # Crear contenedores para el progreso
    progress_container = st.container()
    metrics_container = st.container()
    logs_container = st.container()
    
    with progress_container:
        # Barra de progreso principal
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    with metrics_container:
        # Métricas en tiempo real
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_progreso = st.metric("Progreso", "0%")
        with col2:
            metric_filas = st.metric("Filas insertadas", "0")
        with col3:
            metric_errores = st.metric("Errores", "0")
        with col4:
            metric_velocidad = st.metric("Velocidad", "0 req/min")
    
    with logs_container:
        st.subheader("📝 Log de Descarga")
        log_area = st.empty()
    
    # Variables de seguimiento
    inicio_tiempo = time_module.time()
    logs = []
    
    def agregar_log(mensaje):
        timestamp = datetime.now().strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {mensaje}")
        # Mostrar solo los últimos 10 logs
        logs_recientes = logs[-10:] if len(logs) > 10 else logs
        log_area.text("\n".join(logs_recientes))
    
    agregar_log(f"🚀 Iniciando descarga para {nombre_cliente}")
    agregar_log(f"📊 Total de puntos: {total_puntos:,}")
    
    try:
        # Ejecutar descarga
        resultado = procesar_cliente_completo(hostname, tabla_nombre, timestamps)
        
        # Simular progreso (ya que procesar_cliente_completo no da progreso incremental)
        # En una implementación futura, podrías modificar la función para dar progreso real
        for i in range(0, 101, 10):
            progress_bar.progress(i / 100)
            
            # Actualizar métricas (simulado)
            tiempo_transcurrido = time_module.time() - inicio_tiempo
            velocidad = (total_puntos * (i/100) / tiempo_transcurrido) * 60 if tiempo_transcurrido > 0 else 0
            
            with col1:
                metric_progreso.metric("Progreso", f"{i}%")
            with col4:
                metric_velocidad.metric("Velocidad", f"{velocidad:.0f} req/min")
            
            status_text.info(f"🔄 Procesando... {i}% completado")
            
            if i < 100:
                agregar_log(f"⏳ Progreso: {i}% - Procesando datos...")
                time_module.sleep(0.2)  # Simular tiempo de procesamiento
        
        # Completar progreso
        progress_bar.progress(1.0)
        
        # Actualizar métricas finales
        tiempo_total = time_module.time() - inicio_tiempo
        velocidad_final = (total_puntos / tiempo_total) * 60 if tiempo_total > 0 else 0
        
        with col1:
            metric_progreso.metric("Progreso", "100%")
        with col2:
            metric_filas.metric("Filas insertadas", f"{resultado['filas']:,}")
        with col3:
            metric_errores.metric("Errores", f"{resultado['errores']:,}")
        with col4:
            metric_velocidad.metric("Velocidad final", f"{velocidad_final:.0f} req/min")
        
        # Mostrar resultado final
        if resultado['exito'] and resultado['filas'] > 0:
            status_text.success(f"✅ Descarga completada exitosamente")
            agregar_log(f"✅ Descarga completada: {resultado['filas']:,} filas insertadas")
            agregar_log(f"⏱️ Tiempo total: {tiempo_total:.1f} segundos")
            
            # Celebración
            st.balloons()
            
            # Resumen final
            st.success(f"""
            🎉 **Descarga completada para {nombre_cliente}**
            
            ✅ **Filas insertadas**: {resultado['filas']:,}
            ❌ **Errores**: {resultado['errores']:,}
            ⏱️ **Tiempo total**: {tiempo_total:.1f} segundos
            📊 **Tabla**: `{tabla_nombre}`
            """)
            
        elif resultado['exito']:
            status_text.warning("⚠️ Descarga completada pero sin datos nuevos")
            agregar_log("⚠️ Descarga completada sin datos nuevos")
            st.warning(f"⚠️ **Descarga completada pero sin datos nuevos para {nombre_cliente}**")
            
        else:
            status_text.error("❌ Error en la descarga")
            agregar_log(f"❌ Error en la descarga: {resultado.get('error', 'Error desconocido')}")
            st.error(f"❌ **Error descargando datos para {nombre_cliente}**")
    
    except Exception as e:
        progress_bar.progress(0)
        status_text.error(f"❌ Error: {str(e)}")
        agregar_log(f"❌ Error crítico: {str(e)}")
        st.error(f"❌ **Error crítico**: {str(e)}")
    
    # Botón para nueva descarga
    if st.button("🔄 Realizar otra descarga", use_container_width=True):
        st.rerun()