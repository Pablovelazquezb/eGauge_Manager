import streamlit as st
import pandas as pd
from datetime import datetime
from database.connection import get_connection
from database.models import cargar_clientes

def render_generador_recibos():
    """Calculadora simple de recibos CFE"""
    st.header("🧾 Calculadora CFE")
    
    # Obtener clientes
    clientes_db = cargar_clientes()
    if not clientes_db:
        st.warning("No hay clientes registrados")
        return
    
    # Selección simple
    cliente_opciones = [f"{nombre} ({tabla})" for nombre, _, _, tabla, _ in clientes_db]
    clientes_elegidos = st.multiselect("Seleccionar clientes:", cliente_opciones)
    
    if not clientes_elegidos:
        return
    
    # Selección de columnas por cliente
    columnas_config = {}
    for cliente_elegido in clientes_elegidos:
        # Encontrar tabla correspondiente
        for nombre, _, _, tabla, _ in clientes_db:
            if f"{nombre} ({tabla})" == cliente_elegido:
                st.write(f"**{nombre}** (`{tabla}`)")
                
                # Obtener columnas disponibles
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute(f"""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = %s AND column_name NOT IN ('id', 'created_at', 'timestamp', 'tarifa')
                        AND data_type IN ('numeric', 'double precision', 'real', 'float', 'integer')
                    """, (tabla,))
                    columnas = [row[0] for row in cur.fetchall()]
                    cur.close()
                    conn.close()
                    
                    if columnas:
                        columna_elegida = st.selectbox(
                            f"Columna para {nombre}:",
                            options=columnas,
                            key=f"col_{tabla}"
                        )
                        columnas_config[tabla] = columna_elegida
                    else:
                        st.error(f"No hay columnas numéricas en {tabla}")
                break
    
    if len(columnas_config) != len(clientes_elegidos):
        st.warning("Selecciona una columna para cada cliente")
        return
    
    # Período
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", datetime.now().replace(day=1))
    with col2:
        fecha_fin = st.date_input("Fecha fin", datetime.now())
    
    # Obtener datos
    datos = _obtener_datos_simples(clientes_elegidos, clientes_db, fecha_inicio, fecha_fin, columnas_config)
    
    if datos is not None and not datos.empty:
        _mostrar_calculadora_simple(datos)

def _obtener_datos_simples(clientes_elegidos, clientes_db, fecha_inicio, fecha_fin, columnas_config):
    """Obtiene datos combinados de las tablas seleccionadas"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        todos_datos = []
        
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
        fecha_fin_dt = datetime.combine(fecha_fin, datetime.max.time())
        
        for cliente_elegido in clientes_elegidos:
            # Encontrar tabla correspondiente
            for nombre, _, _, tabla, _ in clientes_db:
                if f"{nombre} ({tabla})" == cliente_elegido:
                    
                    columna = columnas_config.get(tabla)
                    if not columna:
                        continue
                    
                    # Obtener datos
                    cur.execute(f"""
                        SELECT "tarifa", "{columna}" as consumo
                        FROM "{tabla}"
                        WHERE "timestamp" >= %s AND "timestamp" <= %s AND "{columna}" IS NOT NULL
                    """, (fecha_inicio_dt, fecha_fin_dt))
                    
                    datos = cur.fetchall()
                    todos_datos.extend(datos)
                    break
        
        cur.close()
        conn.close()
        
        if todos_datos:
            df = pd.DataFrame(todos_datos, columns=['tarifa', 'consumo'])
            return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def _mostrar_calculadora_simple(datos):
    """Muestra calculadora con los datos solicitados"""
    
    # 1. SUMA DE kWh POR TARIFA
    consumos = datos.groupby('tarifa')['consumo'].sum()
    kwh_base = consumos.get('Base', 0)
    kwh_intermedio = consumos.get('Intermedio', 0)
    kwh_punta = consumos.get('Punta', 0)
    
    # 2. DEMANDA MÁXIMA POR TARIFA
    demandas = datos.groupby('tarifa')['consumo'].max()
    max_base = demandas.get('Base', 0)
    max_intermedio = demandas.get('Intermedio', 0)
    max_punta = demandas.get('Punta', 0)
    
    # 3. CÁLCULO DE DISTRIBUCIÓN (FÓRMULA CFE)
    consumo_total = kwh_base + kwh_intermedio + kwh_punta
    dias_periodo = (datetime.now() - datetime.now().replace(day=1)).days + 1  # Aproximado
    fc = 0.57
    formula_distribucion = consumo_total / (24 * dias_periodo * fc)
    demanda_facturable = min(max_punta, formula_distribucion)
    
    st.subheader("📊 Datos Calculados")
    
    # Mostrar consumos y demandas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("kWh Base", f"{kwh_base:,.1f}")
        st.metric("Max Base", f"{max_base:,.1f} kW")
    with col2:
        st.metric("kWh Intermedio", f"{kwh_intermedio:,.1f}")
        st.metric("Max Intermedio", f"{max_intermedio:,.1f} kW")
    with col3:
        st.metric("kWh Punta", f"{kwh_punta:,.1f}")
        st.metric("Max Punta", f"{max_punta:,.1f} kW")
    
    st.divider()
    
    # PRECIOS EDITABLES
    st.subheader("💰 Precios")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        precio_base = st.number_input("Precio Base ($/kWh)", value=1.20, step=0.01)
        precio_intermedio = st.number_input("Precio Intermedio ($/kWh)", value=1.98, step=0.01)
    with col2:
        precio_punta = st.number_input("Precio Punta ($/kWh)", value=2.32, step=0.01)
        precio_capacidad = st.number_input("Precio Capacidad ($/kW)", value=367.15, step=0.01)
    with col3:
        precio_distribucion = st.number_input("Precio Distribución ($/kW)", value=100.00, step=0.01)
        cargo_fijo = st.number_input("Cargo Fijo ($)", value=563.57, step=0.01)
    with col4:
        # Servicio de Alumbrado Público
        incluir_dap = st.checkbox("Incluir Servicio Alumbrado Público", value=False)
        if incluir_dap:
            porcentaje_dap = st.number_input("% Alumbrado Público", value=2.0, step=0.1, min_value=0.0, max_value=10.0)
        else:
            porcentaje_dap = 0.0
    
    # CÁLCULOS
    costo_base = kwh_base * precio_base
    costo_intermedio = kwh_intermedio * precio_intermedio
    costo_punta = kwh_punta * precio_punta
    costo_capacidad = max(max_base, max_intermedio, max_punta) * precio_capacidad
    costo_distribucion = demanda_facturable * precio_distribucion
    
    # TOTALES COMO SOLICITASTE
    energia = costo_base + costo_intermedio + costo_punta + costo_capacidad + costo_distribucion
    subtotal = energia + cargo_fijo
    
    # Servicio de Alumbrado Público (DAP)
    dap = subtotal * (porcentaje_dap / 100) if incluir_dap else 0
    subtotal_con_dap = subtotal + dap
    
    iva = subtotal_con_dap * 0.16
    total = subtotal_con_dap + iva
    
    st.divider()
    
    # PREVIEW FINAL
    st.subheader("🧾 Preview")
    
    if incluir_dap:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("ENERGÍA", f"${energia:,.2f}")
        with col2:
            st.metric("SUBTOTAL", f"${subtotal:,.2f}")
        with col3:
            st.metric(f"DAP ({porcentaje_dap}%)", f"${dap:,.2f}")
        with col4:
            st.metric("IVA (16%)", f"${iva:,.2f}")
        with col5:
            st.metric("TOTAL", f"${total:,.2f}")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ENERGÍA", f"${energia:,.2f}")
        with col2:
            st.metric("SUBTOTAL", f"${subtotal:,.2f}")
        with col3:
            st.metric("IVA (16%)", f"${iva:,.2f}")
        with col4:
            st.metric("TOTAL", f"${total:,.2f}")
    
    # Desglose simple
    st.write("**Desglose:**")
    st.write(f"• Base: {kwh_base:,.1f} kWh × ${precio_base:.2f} = ${costo_base:,.2f}")
    st.write(f"• Intermedio: {kwh_intermedio:,.1f} kWh × ${precio_intermedio:.2f} = ${costo_intermedio:,.2f}")
    st.write(f"• Punta: {kwh_punta:,.1f} kWh × ${precio_punta:.2f} = ${costo_punta:,.2f}")
    st.write(f"• Capacidad: {max(max_base, max_intermedio, max_punta):,.1f} kW × ${precio_capacidad:.2f} = ${costo_capacidad:,.2f}")
    st.write(f"• Distribución: {demanda_facturable:,.1f} kW × ${precio_distribucion:.2f} = ${costo_distribucion:,.2f}")
    st.write(f"• Cargo Fijo: ${cargo_fijo:,.2f}")
    st.write(f"**• SUBTOTAL: ${subtotal:,.2f}**")
    
    if incluir_dap:
        st.write(f"• Servicio Alumbrado Público ({porcentaje_dap}%): ${subtotal:,.2f} × {porcentaje_dap/100:.3f} = ${dap:,.2f}")
        st.write(f"**• SUBTOTAL + DAP: ${subtotal_con_dap:,.2f}**")
    
    st.write(f"• IVA (16%): ${subtotal_con_dap:,.2f} × 0.16 = ${iva:,.2f}")
    st.write(f"**🔥 TOTAL FINAL: ${total:,.2f}**")
    
    # Guardar datos en session state para el generador de recibos
    st.session_state.datos_calculados = {
        'kwh_base': kwh_base,
        'kwh_intermedio': kwh_intermedio,
        'kwh_punta': kwh_punta,
        'max_base': max_base,
        'max_intermedio': max_intermedio,
        'max_punta': max_punta,
        'costo_base': costo_base,
        'costo_intermedio': costo_intermedio,
        'costo_punta': costo_punta,
        'costo_capacidad': costo_capacidad,
        'costo_distribucion': costo_distribucion,
        'cargo_fijo': cargo_fijo,
        'energia': energia,
        'subtotal': subtotal,
        'subtotal_con_dap': subtotal_con_dap,
        'dap': dap if incluir_dap else 0,
        'iva': iva,
        'total': total,
        'demanda_facturable': demanda_facturable,
        'incluir_dap': incluir_dap,
        'porcentaje_dap': porcentaje_dap if incluir_dap else 0
    }
    
    # Botón para ir al generador de recibos
    if st.button("📄 Crear Recibo CFE", use_container_width=True, type="primary"):
        st.success("✅ Datos guardados. Ve a la pestaña 'Generador Recibos CFE' para crear el recibo visual")
        st.balloons()