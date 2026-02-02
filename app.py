import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time

# --- CONEXIÓN ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Bio-Hypertrophy Log", page_icon="🧬", layout="centered")

st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; text-align: left; padding-left: 20px; }
    .exercise-card { padding: 10px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 5px; background-color: white; }
    .muscle-target { font-size: 0.8em; color: #ff4b4b; font-weight: bold; }
    .fase-box { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px; }
    .done-card { border-left: 8px solid #28a745 !important; background-color: #f8fff9; }
    </style>
    """, unsafe_allow_html=True)

# --- DEFINICIÓN DE RUTINA Y OBJETIVOS SEMANALES ---
# Formato: "Ejercicio": [Series por sesión, Grupo Muscular, Objetivo Semanal]
rutina_detallada = {
    "Espalda-biceps": {
        "Pull Up (Weighted)": [3, "Espalda", "11 series/semana"],
        "Chin Up (Weighted)": [2, "Espalda/Bíceps", "11 series/semana"],
        "Seated Cable Row": [3, "Espalda", "11 series/semana"],
        "Bicep Curl (Barbell)": [4, "Bíceps", "14 series/semana"],
        "Incline Curl": [3, "Bíceps", "14 series/semana"]
    },
    "Pecho-triceps-hombro": {
        "Shoulder Press": [3, "Hombro", "11 series/semana"],
        "Chest Press": [3, "Pecho", "10 series/semana"],
        "Triceps Dip": [3, "Tríceps/Pecho", "12 series/semana"],
        "Lateral Raise": [4, "Hombro", "11 series/semana"],
        "Triceps Extension": [3, "Tríceps", "12 series/semana"],
        "Tríceps Unilateral": [2, "Tríceps", "12 series/semana"]
    },
    "Pierna": {
        "Full Squat": [4, "Cuádriceps", "10 series/semana"],
        "Zancada": [3, "Cuádriceps/Glúteo", "10 series/semana"],
        "Lying Leg Curl": [3, "Isquios", "10 series/semana"],
        "Seated Calf Raise": [4, "Gemelos", "14 series/semana"],
        "Standing Calf Raise": [3, "Gemelos", "14 series/semana"]
    },
    "Tren superior": {
        "Incline Bench Press": [3, "Pecho superior", "10 series/semana"],
        "Seated Cable Row (Wide)": [3, "Espalda/Hombro post", "11 series/semana"],
        "Lateral Raise": [4, "Hombro", "11 series/semana"],
        "Preacher Curl": [3, "Bíceps", "14 series/semana"],
        "Single Arm Triceps Pushdown": [3, "Tríceps", "12 series/semana"]
    }
}

# --- LÓGICA DE ESTADO ---
if "ejercicio_activo" not in st.session_state:
    st.session_state.ejercicio_activo = None

# --- INTERFAZ ---
st.title("🧬 Bio-Hypertrophy Log")

# Planificación 3 Meses
FECHA_INICIO = datetime(2026, 2, 2) 
semana_actual = ((datetime.now() - FECHA_INICIO).days // 7) + 1
fase = "MES 1: ADAPTACIÓN" if semana_actual <= 4 else ("MES 2: SOBRECARGA" if semana_actual <= 8 else "MES 3: INTENSIDAD")

st.markdown(f"<div class='fase-box'><strong>Semana {semana_actual}</strong> | {fase}</div>", unsafe_allow_html=True)

ss = conectar_google_sheets()
dia_actual = st.selectbox("Sesión de hoy", list(rutina_detallada.keys()))
ws = ss.worksheet(dia_actual)
df_all = pd.DataFrame(ws.get_all_records())

# Filtrar lo hecho hoy
hoy_str = datetime.now().strftime("%d/%m/%Y")
if not df_all.empty:
    df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
    hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()
else:
    hechos_hoy = []

# --- LISTA DE EJERCICIOS (Sustituye al desplegable) ---
st.subheader("Lista de Ejercicios")
for ex, info in rutina_detallada[dia_actual].items():
    is_done = ex in hechos_hoy
    done_class = "done-card" if is_done else ""
    
    # Botón de estilo lista
    if st.button(f"{'✅' if is_done else '⚪'} {ex}", key=ex):
        st.session_state.ejercicio_activo = ex

st.divider()

# --- PANEL DE REGISTRO (Solo aparece al seleccionar un ejercicio) ---
if st.session_state.ejercicio_activo:
    ex_active = st.session_state.ejercicio_activo
    info_ex = rutina_detallada[dia_actual][ex_active]
    
    st.markdown(f"### ⚡ Registrando: {ex_active}")
    st.markdown(f"<span class='muscle-target'>Músculo: {info_ex[1]} | Objetivo Semanal: {info_ex[2]}</span>", unsafe_allow_html=True)

    # Buscar última sesión (Referencia)
    if not df_all.empty:
        df_prev = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] != hoy_str)]
        if not df_prev.empty:
            last_date = df_prev['Fecha_Solo'].iloc[-1]
            with st.expander(f"Ver base anterior ({last_date})", expanded=False):
                last_data = df_prev[df_prev['Fecha_Solo'] == last_date]
                for _, r in last_data.iterrows():
                    st.write(f"Serie {r['Serie']}: {r['Peso']}kg x {r['Repeticiones']}")

    # Datos de hoy para auto-relleno
    df_hoy_ex = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] == hoy_str)]
    next_s = len(df_hoy_ex) + 1
    last_p = 0.0 if df_hoy_ex.empty else float(df_hoy_ex.iloc[-1]['Peso'])

    # Input de datos
    c1, c2, c3 = st.columns([1, 2, 2])
    s_val = c1.number_input("S", value=next_s, key="s_input")
    p_val = c2.number_input("Kg", value=last_p, step=0.5, key="p_input")
    r_val = c3.number_input("Reps", value=10, key="r_input")

    if st.button("💾 GUARDAR SERIE", key="save_btn"):
        ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), ex_active, s_val, r_val, p_val, 8, ""])
        st.toast(f"Guardado: {ex_active} S{s_val}")
        time.sleep(1)
        st.rerun()

# --- CRONÓMETRO ---
st.divider()
if "finish_time" not in st.session_state: st.session_state.finish_time = None

st.subheader("⏱️ Descanso")
t_col1, t_col2, t_col3 = st.columns(3)
if t_col1.button("2 MIN"): st.session_state.finish_time = datetime.now() + timedelta(seconds=120)
if t_col2.button("3 MIN"): st.session_state.finish_time = datetime.now() + timedelta(seconds=180)
if t_col3.button("RESET"): st.session_state.finish_time = None

if st.session_state.finish_time:
    rem = (st.session_state.finish_time - datetime.now()).total_seconds()
    if rem > 0:
        m, s = divmod(int(rem), 60)
        st.metric("Próxima serie en...", f"{m:02d}:{s:02d}")
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 ¡TIEMPO CUMPLIDO! 🚨")
        st.session_state.finish_time = Noneballoons()
        st.session_state.finish_time = None
