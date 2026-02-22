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

# --- CONEXIÓN ---
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
    
    # Cargar logs y limpiar pesos (Comas por puntos)
    data = ws_logs.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df['Peso'] = df['Peso'].apply(lambda x: str(x).replace(',', '.')).astype(float)
        df['Repeticiones'] = pd.to_numeric(df['Repeticiones'], errors='coerce').fillna(0)
        
    return ws_logs, ws_config, df

# --- INICIO ---
ss = init_connection()
ws_logs, ws_config, df_logs = get_data(ss)
df_config = pd.DataFrame(ws_config.get_all_records())

st.markdown("### 🧬 Bio-Hypertrophy <span class='highlight'>Pro</span>", unsafe_allow_html=True)
tab_entreno, tab_graficas, tab_config = st.tabs(["🔥 ENTRENAR", "📈 ESTADÍSTICAS", "⚙️ AJUSTES"])

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
            if st.button(label, key=f"btn_{ex_name}"):
                st.session_state.ej_activo = ex_name
                st.session_state.datos_ej_activo = row.to_dict()

    with col_der:
        if "ej_activo" in st.session_state:
            ex_active = st.session_state.ej_activo
            meta = st.session_state.datos_ej_activo
            
            st.markdown(f"#### {ex_active}")
            
            # --- LÓGICA DE SERIES ---
            log_hoy = df_logs[(df_logs['Fecha_Solo'] == hoy_str) & (df_logs['Ejercicio'] == ex_active)]
            n_hechas = len(log_hoy)
            next_serie = n_hechas + 1  # La serie que vas a hacer ahora
            
            # --- MOSTRAR ÚLTIMA SERIE REALIZADA HOY ---
            if not log_hoy.empty:
                ultima_fila = log_hoy.iloc[-1]
                st.markdown(f"""
                <div class="last-set-box">
                    <strong>Anterior Serie (Hecha ahora):</strong> {ultima_fila['Peso']}kg x {ultima_fila['Repeticiones']} reps (RPE {ultima_fila['RPE']})
                </div>
                """, unsafe_allow_html=True)

            # Stats Históricos
            df_ex = df_logs[df_logs['Ejercicio'] == ex_active]
            record_peso = df_ex['Peso'].max() if not df_ex.empty else 0
            
            m1, m2 = st.columns(2)
            m1.markdown(f"<div class='metric-container'><div class='metric-value'>{record_peso} <span style='font-size:12px'>kg</span></div><div class='metric-label'>Récord Histórico</div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-container'><div class='metric-value' style='color:#7ee787'>{next_serie} <span style='font-size:12px'>/ {meta['Series_Default']}</span></div><div class='metric-label'>Serie Actual</div></div>", unsafe_allow_html=True)

            st.divider()

            # --- INPUT DE DATOS ---
            series_target = int(meta['Series_Default'])
            # Barra de progreso: representa lo que estamos completando
            prog = min((next_serie - 1) / series_target, 1.0)
            st.progress(prog)
            st.caption(f"Estas por registrar la **Serie {next_serie}** de {series_target}")

            with st.form("log_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                
                # Sugerir el peso de la serie anterior si existe
                sug_peso = float(log_hoy.iloc[-1]['Peso']) if not log_hoy.empty else 0.0
                if sug_peso == 0 and not df_ex[df_ex['Fecha_Solo'] != hoy_str].empty:
                    sug_peso = float(df_ex[df_ex['Fecha_Solo'] != hoy_str].iloc[-1]['Peso'])

                peso_in = c1.number_input("Peso (kg)", value=sug_peso, step=1.25, format="%.2f")
                reps_in = c2.number_input("Reps", value=10, step=1)
                rpe_in = c3.select_slider("RPE", options=[6, 7, 8, 9, 10], value=8)
                notas_in = st.text_input("Notas")

                if st.form_submit_button("💾 GUARDAR SERIE", type="primary", use_container_width=True):
                    new_row = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        rutina_sel, ex_active, next_serie, reps_in, str(peso_in).replace('.', ','), rpe_in, notas_in
                    ]
                    ws_logs.append_row(new_row)
                    st.toast(f"✅ Serie {next_serie} guardada")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("👈 Selecciona un ejercicio para empezar.")

# --- (El resto de las pestañas se mantienen igual o con leves ajustes de formato) ---



