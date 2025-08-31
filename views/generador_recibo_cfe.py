import streamlit as st
import base64

def render_generador_recibo_cfe():
    """Generador simple de recibos CFE"""
    st.header("📄 Generador de Recibos CFE")
    
    # Verificar datos
    if 'datos_calculados' not in st.session_state:
        st.warning("Primero calcula los datos en 'Calculadora CFE'")
        return
    
    datos = st.session_state.datos_calculados
    
    # Configuración básica
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre Cliente", value="Macrocentro Tultitlán S.A. de C.V.")
        tarifa = st.selectbox("Tarifa", ["GDMTH", "GDMTO", "PDBT", "GDBT"])
    with col2:
        fecha_inicio = st.date_input("Fecha inicio")
        fecha_fin = st.date_input("Fecha fin")
    
    # Generar recibo
    if st.button("Generar Recibo HTML", type="primary"):
        html = _crear_html_simple(nombre, tarifa, fecha_inicio, fecha_fin, datos)
        
        if html:
            _descargar_html(html, f"recibo_{nombre.replace(' ', '_')}.html")
            
            # Mostrar vista previa
            st.markdown("### Vista Previa:")
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.error("Error generando el HTML del recibo")

def _crear_html_simple(nombre, tarifa, fecha_inicio, fecha_fin, datos):
    """Crea HTML básico del recibo"""
    
    fecha_inicio_str = fecha_inicio.strftime('%d %b %y').upper()
    fecha_fin_str = fecha_fin.strftime('%d %b %y').upper()
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Recibo CFE - {nombre}</title>
    <style>
        body {{ font-family: Arial; margin: 20px; }}
        .header {{ text-align: center; color: #0b7a4b; border-bottom: 2px solid #0b7a4b; padding: 10px; }}
        .total-box {{ background: #f0f0f0; border: 2px solid #0b7a4b; padding: 15px; text-align: center; margin: 20px 0; }}
        .total-box .value {{ font-size: 24px; font-weight: bold; color: #0b7a4b; }}
        .section {{ margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .highlight {{ background: #ecfdf5; font-weight: bold; }}
        .total-row {{ background: #0b7a4b; color: white; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>COMISIÓN FEDERAL DE ELECTRICIDAD</h1>
        <h3>SUMINISTRADOR DE SERVICIOS BÁSICOS</h3>
    </div>
    
    <div class="section">
        <strong>{nombre}</strong><br>
        Período: {fecha_inicio_str} - {fecha_fin_str} | Tarifa: {tarifa}
    </div>
    
    <div class="total-box">
        <div>TOTAL A PAGAR:</div>
        <div class="value">${datos['total']:,.2f}</div>
    </div>
    
    <div class="section">
        <h4>CONSUMOS Y DEMANDAS</h4>
        <table>
            <tr><th>Concepto</th><th>Base</th><th>Intermedio</th><th>Punta</th></tr>
            <tr><td>Consumo (kWh)</td><td>{datos['kwh_base']:,.0f}</td><td>{datos['kwh_intermedio']:,.0f}</td><td>{datos['kwh_punta']:,.0f}</td></tr>
            <tr><td>Demanda (kW)</td><td>{datos['max_base']:.0f}</td><td>{datos['max_intermedio']:.0f}</td><td>{datos['max_punta']:.0f}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h4>DESGLOSE DE COSTOS</h4>
        <table>
            <tr><th>Concepto</th><th>Importe</th></tr>
            <tr><td>Energía Base</td><td>${datos['costo_base']:,.2f}</td></tr>
            <tr><td>Energía Intermedia</td><td>${datos['costo_intermedio']:,.2f}</td></tr>
            <tr><td>Energía Punta</td><td>${datos['costo_punta']:,.2f}</td></tr>
            <tr><td>Capacidad</td><td>${datos['costo_capacidad']:,.2f}</td></tr>
            <tr><td>Distribución</td><td>${datos['costo_distribucion']:,.2f}</td></tr>
            <tr class="highlight"><td>Energía Total</td><td>${datos['energia']:,.2f}</td></tr>
            <tr><td>Cargo Fijo</td><td>${datos['cargo_fijo']:,.2f}</td></tr>
            <tr class="highlight"><td>Subtotal</td><td>${datos.get('subtotal_con_dap', datos['subtotal']):,.2f}</td></tr>
            {f'<tr><td>DAP</td><td>${datos["dap"]:,.2f}</td></tr>' if datos.get('dap', 0) > 0 else ''}
            <tr><td>IVA 16%</td><td>${datos['iva']:,.2f}</td></tr>
            <tr class="total-row"><td>TOTAL</td><td>${datos['total']:,.2f}</td></tr>
        </table>
    </div>
    
    <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #666;">
        Recibo generado por eGauge Data Manager
    </div>
</body>
</html>"""
    
    return html

def _descargar_html(html_content, filename):
    """Descarga HTML"""
    try:
        if html_content is None:
            st.error("Error: No se pudo generar el HTML del recibo")
            return
            
        html_bytes = html_content.encode('utf-8')
        b64 = base64.b64encode(html_bytes).decode()
        href = f'<a href="data:text/html;charset=utf-8;base64,{b64}" download="{filename}">⬇️ Descargar {filename}</a>'
        st.markdown(href, unsafe_allow_html=True)
        st.success(f"✅ {filename} listo")
    except Exception as e:
        st.error(f"Error: {e}")