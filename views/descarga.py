import streamlit as st
import time as time_module
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from database.models import cargar_clientes
from core.processor import generar_timestamps_rango
from core.downloader import procesar_cliente_completo

def render_descarga_masiva():
    """Renderiza la vista de descarga masiva"""
    st.header("📊 Descarga Masiva")
    st.markdown("**Descarga datos para tus clientes registrados**")
    
    # Cargar clientes activos
    clientes_db = cargar_clientes()
    
    if not clientes_db:
        st.warning("⚠️ No tienes clientes activos registrados")
        st.info("💡 Ve a la pestaña 'Gestión de Clientes' para agregar clientes primero")
        return
    
    # Configuración en la misma vista
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Selector de clientes
        clientes_seleccionados = _selector_clientes(clientes_db)
    
    with col2:
        # Configuración temporal y paralelismo
        datetime_inicio, datetime_fin = _configurar_periodo()
        max_workers_clientes, mostrar_progreso_detallado = _configurar_paralelismo()
    
    if not clientes_seleccionados:
        st.info("ℹ️ Selecciona al menos un cliente para continuar")
        return
    
    # Botón de descarga
    if st.button("🚀 Iniciar Descarga Paralela", type="primary"):
        _ejecutar_descarga_paralela(
            clientes_seleccionados,
            datetime_inicio,
            datetime_fin,
            max_workers_clientes,
            mostrar_progreso_detallado
        )

def _configurar_periodo():
    """Configura el período temporal directamente en la vista"""
    st.subheader("⏰ Configuración Temporal")
    
    modo = st.radio("Período:", ["📅 Mes completo", "📆 Rango personalizado"], horizontal=True)
    
    if modo == "📅 Mes completo":
        col1, col2 = st.columns(2)
        with col1:
            años_disponibles = list(range(2020, datetime.now().year + 1))
            año = st.selectbox("Año", años_disponibles, index=len(años_disponibles) - 1)
        with col2:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_nombre = st.selectbox("Mes", meses, index=datetime.now().month - 1)
            mes = meses.index(mes_nombre) + 1
        
        # Sobrado automático: del día 1 del mes hasta el día 1 del mes siguiente
        datetime_inicio = datetime(año, mes, 1, 0, 0, 0)
        if mes == 12:
            datetime_fin = datetime(año + 1, 1, 1, 23, 0, 0)
        else:
            datetime_fin = datetime(año, mes + 1, 1, 23, 0, 0)
        
        # Mostrar información del período
        total_horas = int((datetime_fin - datetime_inicio).total_seconds() / 3600) + 1
        st.info(f"📅 **{mes_nombre} {año}**: ~{total_horas} horas")
        
    else:
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio")
            hora_inicio = st.time_input("Hora inicio")
        with col2:
            fecha_fin = st.date_input("Fecha fin")
            hora_fin = st.time_input("Hora fin")
        
        datetime_inicio = datetime.combine(fecha_inicio, hora_inicio)
        datetime_fin = datetime.combine(fecha_fin, hora_fin)
        
        total_horas = int((datetime_fin - datetime_inicio).total_seconds() / 3600) + 1
        st.info(f"⏱️ Total: ~{total_horas} horas")
    
    return datetime_inicio, datetime_fin

def _configurar_paralelismo():
    """Configura las opciones de paralelismo"""
    st.subheader("⚡ Configuración de Rendimiento")
    
    max_workers_clientes = st.slider(
        "Clientes en paralelo", 
        min_value=1, 
        max_value=20, 
        value=5,
        help="Cuántos clientes procesar simultáneamente"
    )
    
    mostrar_progreso_detallado = st.checkbox(
        "Mostrar progreso detallado", 
        value=False,
        help="Muestra el progreso de cada cliente individualmente"
    )
    
    # Información sobre la configuración
    st.caption(f"🔧 {max_workers_clientes} clientes × 10 threads = hasta {max_workers_clientes * 10} requests simultáneos")
    
    return max_workers_clientes, mostrar_progreso_detallado

def _selector_clientes(clientes_db):
    """Renderiza el selector de clientes"""
    st.subheader("👥 Seleccionar Clientes")
    
    modo_seleccion = st.radio(
        "¿Qué clientes descargar?",
        ["✅ Todos los activos", "🎯 Selección personalizada"],
        horizontal=True
    )
    
    if modo_seleccion == "✅ Todos los activos":
        clientes_seleccionados = [(hostname, tabla) for _, hostname, _, tabla, _ in clientes_db]
        st.success(f"✅ Se descargarán datos para {len(clientes_seleccionados)} clientes activos")
        
        # Mostrar lista en formato compacto
        if len(clientes_db) <= 10:
            with st.expander("👀 Ver clientes seleccionados"):
                for nombre, hostname, _, tabla, _ in clientes_db:
                    st.write(f"• **{nombre}** → `{tabla}`")
        else:
            st.info(f"📋 Demasiados clientes para mostrar ({len(clientes_db)}). Usa 'Selección personalizada' para ver la lista.")
        
        return clientes_seleccionados
    
    else:
        # Selección personalizada con checkboxes más compactos
        st.write("Selecciona los clientes para descargar:")
        
        clientes_seleccionados = []
        
        # Usar columnas para mostrar más clientes
        cols = st.columns(2)
        
        for idx, (nombre, hostname, url, tabla, cliente_id) in enumerate(clientes_db):
            with cols[idx % 2]:
                selected = st.checkbox(
                    f"**{nombre}**",
                    key=f"cliente_{cliente_id}",
                    help=f"Tabla: {tabla} | Host: {hostname}"
                )
                
                if selected:
                    clientes_seleccionados.append((hostname, tabla))
        
        if clientes_seleccionados:
            st.success(f"✅ {len(clientes_seleccionados)} clientes seleccionados")
        
        return clientes_seleccionados

def _ejecutar_descarga_paralela(clientes_seleccionados, datetime_inicio, datetime_fin, max_workers_clientes, mostrar_progreso_detallado):
    """Ejecuta la descarga paralela"""
    # Generar timestamps
    timestamps = generar_timestamps_rango(datetime_inicio, datetime_fin, 3600)
    total_requests = len(clientes_seleccionados) * len(timestamps)
    
    st.info(f"🚀 **Descarga paralela iniciada**: {len(clientes_seleccionados)} clientes × {len(timestamps)} puntos = {total_requests:,} requests totales")
    
    # Inicializar contadores y UI
    total_filas = 0
    total_errores = 0
    clientes_completados = 0
    
    # Métricas en tiempo real
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_clientes = st.metric("Clientes completados", "0")
    with col2:
        metric_filas = st.metric("Total filas", "0")
    with col3:
        metric_errores = st.metric("Total errores", "0")
    with col4:
        metric_velocidad = st.metric("Velocidad", "0 req/min")
    
    # Progress bar principal
    progress_principal = st.progress(0)
    status_principal = st.empty()
    
    # Contenedor para progreso detallado
    if mostrar_progreso_detallado:
        progreso_detallado = st.container()
        detalles_clientes = {}
    
    # Función para procesar cliente
    def procesar_cliente_wrapper(args):
        hostname, tabla_nombre = args
        try:
            resultado = procesar_cliente_completo(hostname, tabla_nombre, timestamps)
            return resultado
        except Exception as e:
            return {
                'tabla': tabla_nombre,
                'filas': 0,
                'errores': len(timestamps),
                'exito': False,
                'error': str(e)
            }
    
    # Tiempo de inicio
    inicio_tiempo = time_module.time()
    
    # Procesar clientes en paralelo
    with ThreadPoolExecutor(max_workers=max_workers_clientes) as executor:
        # Enviar todos los clientes
        future_to_cliente = {
            executor.submit(procesar_cliente_wrapper, cliente): cliente 
            for cliente in clientes_seleccionados
        }
        
        # Procesar resultados conforme van llegando
        for future in as_completed(future_to_cliente):
            hostname, tabla_nombre = future_to_cliente[future]
            
            try:
                resultado = future.result()
                
                # Actualizar contadores
                total_filas += resultado['filas']
                total_errores += resultado['errores']
                clientes_completados += 1
                
                # Calcular velocidad
                tiempo_transcurrido = time_module.time() - inicio_tiempo
                requests_completados = clientes_completados * len(timestamps)
                velocidad = (requests_completados / tiempo_transcurrido) * 60 if tiempo_transcurrido > 0 else 0
                
                # Actualizar métricas
                with col1:
                    metric_clientes.metric("Clientes completados", f"{clientes_completados}/{len(clientes_seleccionados)}")
                with col2:
                    metric_filas.metric("Total filas", f"{total_filas:,}")
                with col3:
                    metric_errores.metric("Total errores", f"{total_errores:,}")
                with col4:
                    metric_velocidad.metric("Velocidad", f"{velocidad:.0f} req/min")
                
                # Actualizar progress bar
                progreso = clientes_completados / len(clientes_seleccionados)
                progress_principal.progress(progreso)
                
                # Status principal
                porcentaje = progreso * 100
                eta_minutos = ((tiempo_transcurrido / clientes_completados) * (len(clientes_seleccionados) - clientes_completados)) / 60 if clientes_completados > 0 else 0
                status_principal.info(f"🔄 Progreso: {porcentaje:.1f}% - ETA: {eta_minutos:.1f} minutos")
                
                # Mostrar resultado del cliente
                if resultado['exito'] and resultado['filas'] > 0:
                    st.success(f"✅ **{tabla_nombre}**: {resultado['filas']:,} filas insertadas")
                elif resultado['exito']:
                    st.warning(f"⚠️ **{tabla_nombre}**: Completado sin datos")
                else:
                    error_msg = resultado.get('error', 'Error desconocido')
                    st.error(f"❌ **{tabla_nombre}**: {error_msg}")
                
                # Progreso detallado si está habilitado
                if mostrar_progreso_detallado:
                    with progreso_detallado:
                        if tabla_nombre not in detalles_clientes:
                            detalles_clientes[tabla_nombre] = st.empty()
                        
                        status = "✅ Completado" if resultado['exito'] else "❌ Error"
                        detalles_clientes[tabla_nombre].write(
                            f"**{tabla_nombre}**: {status} - {resultado['filas']:,} filas, {resultado['errores']} errores"
                        )
            
            except Exception as e:
                st.error(f"❌ **{tabla_nombre}**: Error procesando - {str(e)}")
                clientes_completados += 1
    
    # Finalizar
    tiempo_total = time_module.time() - inicio_tiempo
    
    # Limpiar UI de progreso
    progress_principal.empty()
    status_principal.empty()
    
    # Mostrar resumen final
    st.balloons()
    st.success(f"🎉 **Descarga paralela completada en {tiempo_total/60:.1f} minutos**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Clientes procesados", len(clientes_seleccionados))
    with col2:
        st.metric("📊 Total filas insertadas", f"{total_filas:,}")
    with col3:
        velocidad_promedio = (total_requests / tiempo_total) * 60 if tiempo_total > 0 else 0
        st.metric("⚡ Velocidad promedio", f"{velocidad_promedio:.0f} req/min")
    
    st.info(f"💡 **Eficiencia**: {total_requests:,} requests completados - {total_errores:,} errores ({(total_errores/total_requests*100):.1f}% error rate)")

    
    # Inicializar contadores y UI
    total_filas = 0
    total_errores = 0
    clientes_completados = 0
    
    # Métricas en tiempo real
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_clientes = st.metric("Clientes completados", "0")
    with col2:
        metric_filas = st.metric("Total filas", "0")
    with col3:
        metric_errores = st.metric("Total errores", "0")
    with col4:
        metric_velocidad = st.metric("Velocidad", "0 req/min")
    
    # Progress bar principal
    progress_principal = st.progress(0)
    status_principal = st.empty()
    
    # Contenedor para progreso detallado
    if mostrar_progreso_detallado:
        progreso_detallado = st.container()
        detalles_clientes = {}
    
    # Función para procesar cliente con conexión individual
    def procesar_cliente_wrapper(args):
        hostname, tabla_nombre = args
        try:
            resultado = procesar_cliente_completo(hostname, tabla_nombre, timestamps)
            return resultado
        except Exception as e:
            return {
                'tabla': tabla_nombre,
                'filas': 0,
                'errores': len(timestamps),
                'exito': False,
                'error': str(e)
            }
    
    # Tiempo de inicio
    inicio_tiempo = time_module.time()
    
    # Procesar clientes en paralelo
    with ThreadPoolExecutor(max_workers=max_workers_clientes) as executor:
        # Enviar todos los clientes
        future_to_cliente = {
            executor.submit(procesar_cliente_wrapper, cliente): cliente 
            for cliente in clientes_seleccionados
        }
        
        # Procesar resultados conforme van llegando
        for future in as_completed(future_to_cliente):
            hostname, tabla_nombre = future_to_cliente[future]
            
            try:
                resultado = future.result()
                
                # Actualizar contadores
                total_filas += resultado['filas']
                total_errores += resultado['errores']
                clientes_completados += 1
                
                # Calcular velocidad
                tiempo_transcurrido = time_module.time() - inicio_tiempo
                requests_completados = clientes_completados * len(timestamps)
                velocidad = (requests_completados / tiempo_transcurrido) * 60 if tiempo_transcurrido > 0 else 0
                
                # Actualizar métricas
                with col1:
                    metric_clientes.metric("Clientes completados", f"{clientes_completados}/{len(clientes_seleccionados)}")
                with col2:
                    metric_filas.metric("Total filas", f"{total_filas:,}")
                with col3:
                    metric_errores.metric("Total errores", f"{total_errores:,}")
                with col4:
                    metric_velocidad.metric("Velocidad", f"{velocidad:.0f} req/min")
                
                # Actualizar progress bar
                progreso = clientes_completados / len(clientes_seleccionados)
                progress_principal.progress(progreso)
                
                # Status principal
                porcentaje = progreso * 100
                eta_minutos = ((tiempo_transcurrido / clientes_completados) * (len(clientes_seleccionados) - clientes_completados)) / 60 if clientes_completados > 0 else 0
                status_principal.info(f"🔄 Progreso: {porcentaje:.1f}% - ETA: {eta_minutos:.1f} minutos")
                
                # Mostrar resultado del cliente
                if resultado['exito'] and resultado['filas'] > 0:
                    st.success(f"✅ **{tabla_nombre}**: {resultado['filas']:,} filas insertadas")
                elif resultado['exito']:
                    st.warning(f"⚠️ **{tabla_nombre}**: Completado sin datos")
                else:
                    error_msg = resultado.get('error', 'Error desconocido')
                    st.error(f"❌ **{tabla_nombre}**: {error_msg}")
                
                # Progreso detallado si está habilitado
                if mostrar_progreso_detallado:
                    with progreso_detallado:
                        if tabla_nombre not in detalles_clientes:
                            detalles_clientes[tabla_nombre] = st.empty()
                        
                        status = "✅ Completado" if resultado['exito'] else "❌ Error"
                        detalles_clientes[tabla_nombre].write(
                            f"**{tabla_nombre}**: {status} - {resultado['filas']:,} filas, {resultado['errores']} errores"
                        )
            
            except Exception as e:
                st.error(f"❌ **{tabla_nombre}**: Error procesando - {str(e)}")
                clientes_completados += 1
    
    # Finalizar
    tiempo_total = time_module.time() - inicio_tiempo
    
    # Limpiar UI de progreso
    progress_principal.empty()
    status_principal.empty()
    
    # Mostrar resumen final
    st.balloons()
    st.success(f"🎉 **Descarga paralela completada en {tiempo_total/60:.1f} minutos**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Clientes procesados", len(clientes_seleccionados))
    with col2:
        st.metric("📊 Total filas insertadas", f"{total_filas:,}")
    with col3:
        velocidad_promedio = (total_requests / tiempo_total) * 60 if tiempo_total > 0 else 0
        st.metric("⚡ Velocidad promedio", f"{velocidad_promedio:.0f} req/min")
    
    st.info(f"💡 **Eficiencia**: {total_requests:,} requests completados - {total_errores:,} errores ({(total_errores/total_requests*100):.1f}% error rate)")