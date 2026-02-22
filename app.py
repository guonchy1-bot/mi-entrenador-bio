import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import time
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

# --- DISEÑO & CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0e1117; }
    .metric-container {
        background-color: #1a1c24;
        border: 1px solid #2d333b;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-value { font-size: 24px; font-weight: 800; color: #58a6ff; }
    .metric-label { font-size: 12px; color: #8b949e; text-transform: uppercase; margin-top: 5px; }
    .last-set-box {
        background-color: #21262d;
        border-left: 5px solid #7ee787;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN Y EXTRACCIÓN DE DATOS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

def get_data(ss):
    ws_logs = ss.worksheet("Logs_Entrenamiento")
    ws_config = ss.worksheet("Config_Rutinas")
    
    # Usamos get_all_values para evitar que gspread arruine los decimales europeos
    data = ws_logs.get_all_values()
    
    if len(data) > 1:
        headers = data[0]
        df = pd.DataFrame(data[1:], columns=headers)
        
        # Limpiamos Peso y Repeticiones manualmente de forma segura
        df['Peso'] = df['Peso'].astype(str).str.replace(',', '.')
        df['Peso'] = pd.to_numeric(df['Peso'], errors='coerce').fillna(0.0)
        
        df['Repeticiones'] = df['Repeticiones'].astype(str).str.replace(',', '.')
        df['Repeticiones'] = pd.to_numeric(df['Repeticiones'], errors='coerce').fillna(0)
    else:
        # Si la hoja está vacía (solo cabeceras)
        df = pd.DataFrame(columns=data[0] if data else [])
        
    return ws_logs, ws_config, df

# --- FUNCIÓN DE CONSEJO INTELIGENTE (COACH) ---
def obtener_consejo_coach(df_ex):
    if df_ex.empty:
        return "✨ **¡Primer registro!** Establece una base sólida hoy para poder superarte la próxima semana."
    
    df_temp = df_ex.copy()
    df_temp['Fecha_Dia'] = df_temp['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
    hoy_str = datetime.now().strftime("%d/%m/%Y")
    
    sesiones_pasadas = df_temp[df_temp['Fecha_Dia'] != hoy_str]
    
    if sesiones_pasadas.empty:
        return "🎯 **Segunda serie del día:** Intenta mantener la intensidad de la primera."

    ultima_fecha = sesiones_pasadas['Fecha_Dia'].iloc[-1]
    datos_last = sesiones_pasadas[sesiones_pasadas['Fecha_Dia'] == ultima_fecha]
    
    mejor_peso = datos_last['Peso'].max()
    mejor_reps = datos_last[datos_last['Peso'] == mejor_peso]['Repeticiones'].max()

    if mejor_peso == 0:
        return f"💪 La última vez hiciste peso corporal. **Reto:** Intenta hacer {int(mejor_reps + 1)} repeticiones hoy."
    
    consejo = f"💡 **Récord anterior ({ultima_fecha}):** {mejor_peso}kg x {int(mejor_reps)} reps. "
    consejo += f"\n\n**Tu objetivo hoy:** ¡Haz {int(mejor_reps + 1)} reps con {mejor_peso}kg O mantén las {int(mejor_reps)} reps pero sube a {mejor_peso + 1.25}kg!"
    
    return consejo

# --- INICIO DE LA APLICACIÓN ---
ss = init_connection()
ws_logs, ws_config, df_logs = get_data(ss)

# Para la config, get_all_records() es seguro porque no hay decimales problemáticos ahí
df_config = pd.DataFrame(ws_config.get_all_records())

st.markdown("### 🧬 Bio-Hypertrophy <span class='highlight'>Pro</span>", unsafe_allow_html=True)
tab_entreno, tab_graficas, tab_config = st.tabs(["🔥 ENTRENAR", "📈 ESTADÍSTICAS", "⚙️ AJUSTES"])

# ==========================================
# PESTAÑA 1: ENTRENAMIENTO
# ==========================================
with tab_entreno:
    if not df_config.empty:
        rutinas = df_config['Rutina'].unique().tolist()
        rutina_sel = st.selectbox("Selecciona tu sesión", rutinas)
        ejercicios_rutina = df_config[df_config['Rutina'] == rutina_sel]
    
    col_izq, col_der = st.columns([1, 1.8], gap="medium")

    with col_izq:
        st.markdown("##### 📋 Ejercicios")
        hoy_str = datetime.now().strftime("%d/%m/%Y")
        hechos_hoy = []
        if not df_logs.empty:
            df_logs['Fecha_Solo'] = df_logs['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
            hechos_hoy = df_logs[df_logs['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

        for _, row in ejercicios_rutina.iterrows():
            ex_name = row['Ejercicio']
            label = f"{'✅' if ex_name in hechos_hoy else '⚪'} {ex_name}"
            if st.button(label, key=f"btn_{ex_name}", use_container_width=True):
                st.session_state.ej_activo = ex_name
                st.session_state.datos_ej_activo = row.to_dict()

    with col_der:
        if "ej_activo" in st.session_state:
            ex_active = st.session_state.ej_activo
            meta = st.session_state.datos_ej_activo
            
            st.markdown(f"#### {ex_active}")
            
            # --- LÓGICA DE SERIES ---
            log_hoy = df_logs[(df_logs['Fecha_Solo'] == hoy_str) & (df_logs['Ejercicio'] == ex_active)] if not df_logs.empty else pd.DataFrame()
            n_hechas = len(log_hoy)
            next_serie = n_hechas + 1  
            
            # --- MOSTRAR ÚLTIMA SERIE REALIZADA HOY ---
            if not log_hoy.empty:
                ultima_fila = log_hoy.iloc[-1]
                st.markdown(f"""
                <div class="last-set-box">
                    <strong>Anterior Serie (Hecha ahora):</strong> {ultima_fila['Peso']}kg x {ultima_fila['Repeticiones']} reps (RPE {ultima_fila['RPE']})
                </div>
                """, unsafe_allow_html=True)

            # --- STATS HISTÓRICOS ---
            df_ex = df_logs[df_logs['Ejercicio'] == ex_active] if not df_logs.empty else pd.DataFrame()
            record_peso = df_ex['Peso'].max() if not df_ex.empty else 0
            
            m1, m2 = st.columns(2)
            m1.markdown(f"<div class='metric-container'><div class='metric-value'>{record_peso} <span style='font-size:12px'>kg</span></div><div class='metric-label'>Récord Histórico</div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-container'><div class='metric-value' style='color:#7ee787'>{next_serie} <span style='font-size:12px'>/ {meta['Series_Default']}</span></div><div class='metric-label'>Serie Actual</div></div>", unsafe_allow_html=True)

            st.divider()
            
            # Mostrar el consejo del Coach JUSTO ANTES del formulario
            consejo = obtener_consejo_coach(df_ex)
            st.info(consejo)

            # --- INPUT DE DATOS ---
            series_target = int(meta['Series_Default'])
            prog = min((next_serie - 1) / series_target, 1.0)
            st.progress(prog)
            st.caption(f"Estás por registrar la **Serie {next_serie}** de {series_target}")

            with st.form("log_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                
                # Sugerir el peso de la serie anterior si existe
                sug_peso = float(log_hoy.iloc[-1]['Peso']) if not log_hoy.empty else 0.0
                if sug_peso == 0 and not df_ex.empty:
                    sesiones_previas = df_ex[df_ex['Fecha_Solo'] != hoy_str]
                    if not sesiones_previas.empty:
                        sug_peso = float(sesiones_previas.iloc[-1]['Peso'])

                peso_in = c1.number_input("Peso (kg)", value=sug_peso, step=1.25, format="%.2f")
                reps_in = c2.number_input("Reps", value=10, step=1)
                rpe_in = c3.select_slider("RPE", options=[6, 7, 8, 9, 10], value=8)
                notas_in = st.text_input("Notas")

                if st.form_submit_button("💾 GUARDAR SERIE", type="primary", use_container_width=True):
                    new_row = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        rutina_sel, 
                        ex_active, 
                        next_serie, 
                        reps_in, 
                        peso_in,  # ENVÍA EL FLOAT PURO, USER_ENTERED SE ENCARGA DEL FORMATO
                        rpe_in, 
                        notas_in
                    ]
                    ws_logs.append_row(new_row, value_input_option='USER_ENTERED')
                    
                    st.toast(f"✅ Serie {next_serie} guardada")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("👈 Selecciona un ejercicio en el panel izquierdo para empezar.")

# ==========================================
# PESTAÑA 2: ESTADÍSTICAS (GRÁFICAS ESTÁTICAS)
# ==========================================
with tab_graficas:
    st.markdown("### 📈 Evolución por Ejercicio")
    
    if df_logs.empty:
        st.info("Aún no hay datos suficientes para mostrar gráficas.")
    else:
        # Selección de ejercicio
        ejercicios_disp = sorted(df_logs['Ejercicio'].unique().tolist())
        ej_seleccionado = st.selectbox("Selecciona el Ejercicio para analizar:", ejercicios_disp)
        
        df_graf = df_logs[df_logs['Ejercicio'] == ej_seleccionado].copy()
        
        if not df_graf.empty:
            # Asegurar que Fecha_Solo existe (puede no existir si el usuario entra directo a gráficas)
            if 'Fecha_Solo' not in df_graf.columns:
                df_graf['Fecha_Solo'] = df_graf['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
                
            df_graf['Fecha_DT'] = pd.to_datetime(df_graf['Fecha_Solo'], format="%d/%m/%Y")
            
            # Calcular Volumen de la serie (Peso * Reps) y agregarlo por día
            df_graf['Volumen_Serie'] = df_graf['Peso'] * df_graf['Repeticiones']
            
            df_agrupado = df_graf.groupby('Fecha_DT').agg(
                Peso_Maximo=('Peso', 'max'),
                Volumen_Total=('Volumen_Serie', 'sum')
            ).reset_index()
            
            st.divider()
            
            # Gráfica 1: Récord de Peso
            fig_peso = px.line(df_agrupado, x='Fecha_DT', y='Peso_Maximo', markers=True, 
                               title=f"Evolución del Peso Máximo - {ej_seleccionado}",
                               labels={'Fecha_DT': 'Fecha', 'Peso_Maximo': 'Kilos (kg)'},
                               color_discrete_sequence=['#58a6ff'])
            
            # config={'staticPlot': True} desactiva la interactividad para evitar problemas al hacer scroll en el móvil
            st.plotly_chart(fig_peso, use_container_width=True, config={'staticPlot': True})
            
            # Gráfica 2: Volumen Total
            fig_vol = px.bar(df_agrupado, x='Fecha_DT', y='Volumen_Total', 
                             title=f"Volumen Total (kg totales movidos) - {ej_seleccionado}",
                             labels={'Fecha_DT': 'Fecha', 'Volumen_Total': 'Volumen (kg)'},
                             color_discrete_sequence=['#7ee787'])
            
            st.plotly_chart(fig_vol, use_container_width=True, config={'staticPlot': True})

# ==========================================
# PESTAÑA 3: AJUSTES (AÑADIR/ELIMINAR)
# ==========================================
with tab_config:
    st.markdown("### ⚙️ Gestión de Rutinas")
    
    if df_config.empty:
        st.warning("No se pudo cargar la configuración de rutinas.")
    else:
        rutinas_existentes = df_config['Rutina'].unique().tolist()
        
        # --- SECCIÓN AÑADIR ---
        with st.expander("➕ Añadir nuevo ejercicio"):
            with st.form("form_add_ex", clear_on_submit=True):
                col1, col2 = st.columns(2)
                rut_add = col1.selectbox("¿A qué rutina lo añades?", rutinas_existentes)
                nombre_add = col2.text_input("Nombre del Ejercicio")
                
                col3, col4, col5 = st.columns(3)
                series_add = col3.number_input("Series Default", min_value=1, value=3, step=1)
                musculo_add = col4.text_input("Músculo objetivo")
                reps_add = col5.text_input("Reps Objetivo (ej. 8-12)")
                
                if st.form_submit_button("Añadir al Plan", type="primary"):
                    if nombre_add and musculo_add:
                        nuevo_ejercicio = [rut_add, nombre_add, series_add, musculo_add, reps_add]
                        ws_config.append_row(nuevo_ejercicio)
                        st.success(f"✅ '{nombre_add}' añadido a {rut_add}.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Rellena al menos el Nombre y el Músculo.")
                        
        # --- SECCIÓN ELIMINAR ---
        with st.expander("🗑️ Eliminar ejercicio"):
            with st.form("form_del_ex"):
                st.warning("⚠️ Esta acción borrará el ejercicio de tu configuración actual (no de los logs pasados).")
                rut_del = st.selectbox("Selecciona la rutina", rutinas_existentes, key="rut_del")
                
                ejs_en_rutina = df_config[df_config['Rutina'] == rut_del]['Ejercicio'].tolist()
                ej_del = st.selectbox("Ejercicio a eliminar", ejs_en_rutina)
                
                if st.form_submit_button("Eliminar permanentemente"):
                    # Buscar la fila exacta en el dataframe
                    idx = df_config[(df_config['Rutina'] == rut_del) & (df_config['Ejercicio'] == ej_del)].index
                    
                    if not idx.empty:
                        # Convertimos a entero. +2 porque el DF tiene índice base 0, y la fila 1 en Sheets es la cabecera.
                        fila_sheet = int(idx[0]) + 2 
                        ws_config.delete_rows(fila_sheet)
                        st.success(f"🗑️ '{ej_del}' eliminado correctamente.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("No se encontró el ejercicio.")



