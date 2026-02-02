import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time
import requests

# --- CONEXIÓN ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

# --- LÓGICA DE NOTIFICACIÓN TELEGRAM ---
def enviar_notificacion(mensaje):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={'chat_id': chat_id, 'text': mensaje})
    except:
        pass # Si no están configurados los secrets, ignora el envío

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Bio-Log Pro Plan", page_icon="⚡", layout="centered")

# CSS Profesional
st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 50px; border-radius: 12px; }
    .done { color: #28a745; font-weight: bold; border: 2px solid #28a745; padding: 5px; border-radius: 5px; background-color: #e8f5e9; }
    .pending { color: #6c757d; border: 2px solid #dee2e6; padding: 5px; border-radius: 5px; }
    .fase-box { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px; }
    .last-session-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #FF4B4B; }
    </style>
    """, unsafe_allow_html=True)

# --- PLANIFICACIÓN DE 3 MESES ---
FECHA_INICIO = datetime(2026, 2, 2) # Ajusta a tu fecha de inicio real
hoy = datetime.now()
semana_actual = ((hoy - FECHA_INICIO).days // 7) + 1

def obtener_fase(semana):
    if semana <= 4: return "MES 1: ADAPTACIÓN (RPE 7-8, foco técnica)"
    if semana <= 8: return "MES 2: SOBRECARGA (+2.5kg en básicos, +1 rep aislamiento)"
    return "MES 3: INTENSIDAD (RPE 9-10, series al fallo técnico)"

# --- RUTINA ---
rutina = {
    "Espalda-biceps": ["Pull Up (Weighted)", "Chin Up (Weighted)", "Seated Cable Row", "Bicep Curl (Barbell)", "Incline Curl"],
    "Pecho-triceps-hombro": ["Shoulder Press", "Chest Press", "Triceps Dip", "Lateral Raise", "Triceps Extension", "Tríceps Unilateral"],
    "Pierna": ["Full Squat", "Zancada", "Lying Leg Curl", "Seated Calf Raise", "Standing Calf Raise"],
    "Tren superior": ["Incline Bench Press", "Seated Cable Row (Wide)", "Lateral Raise", "Preacher Curl", "Single Arm Triceps Pushdown"]
}

# --- INTERFAZ ---
st.title("🔋 Bio-Log Pro")

# Caja de Fase Actual
st.markdown(f"""
<div class='fase-box'>
    <strong>📅 Semana {semana_actual}</strong><br>
    🎯 Objetivo: {obtener_fase(semana_actual)}
</div>
""", unsafe_allow_html=True)

ss = conectar_google_sheets()
dia_actual = st.selectbox("Selecciona Sesión", list(rutina.keys()))
ws = ss.worksheet(dia_actual)
df_all = pd.DataFrame(ws.get_all_records())

# Filtrar HOY
hoy_str = hoy.strftime("%d/%m/%Y")
if not df_all.empty:
    df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
    ejercicios_hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()
else:
    ejercicios_hechos_hoy = []

# --- 1. PROGRESO DE LA SESIÓN ---
st.subheader("Estado de hoy")
cols = st.columns(len(rutina[dia_actual]))
for i, ex in enumerate(rutina[dia_actual]):
    is_done = ex in ejercicios_hechos_hoy
    label = f"✅ {ex}" if is_done else f"⚪ {ex}"
    color = "done" if is_done else "pending"
    st.markdown(f"<div class='{color}' style='font-size: 0.8em; text-align: center;'>{label}</div>", unsafe_allow_html=True)

st.divider()

# --- 2. REGISTRO Y REFERENCIA ---
ejercicio_sel = st.selectbox("Registrar Ejercicio", rutina[dia_actual])

if not df_all.empty:
    df_prev = df_all[(df_all['Ejercicio'] == ejercicio_sel) & (df_all['Fecha_Solo'] != hoy_str)]
    if not df_prev.empty:
        last_date = df_prev['Fecha_Solo'].iloc[-1]
        st.markdown(f"<div class='last-session-box'><strong>Base anterior ({last_date}):</strong>", unsafe_allow_html=True)
        last_data = df_prev[df_prev['Fecha_Solo'] == last_date]
        for _, r in last_data.iterrows():
            st.write(f"S{r['Serie']}: {r['Peso']}kg x {r['Repeticiones']}")
        st.markdown("</div>", unsafe_allow_html=True)

# Formulario de serie
df_hoy = df_all[(df_all['Ejercicio'] == ejercicio_sel) & (df_all['Fecha_Solo'] == hoy_str)]
next_s = len(df_hoy) + 1
last_p = 0.0 if df_hoy.empty else float(df_hoy.iloc[-1]['Peso'])

c1, c2, c3 = st.columns([1, 2, 2])
s_val = c1.number_input("S", value=next_s)
p_val = c2.number_input("Kg", value=last_p, step=0.5)
r_val = c3.number_input("Reps", value=10)

if st.button("💾 GUARDAR SERIE"):
    ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), ejercicio_sel, s_val, r_val, p_val, 8, ""])
    st.success("Guardado")
    time.sleep(1)
    st.rerun()

# --- 3. CRONÓMETRO PERSISTENTE ---
st.divider()
st.subheader("⏱️ Descanso")

if "finish_time" not in st.session_state:
    st.session_state.finish_time = None
    st.session_state.notified = False

t_c1, t_c2, t_c3 = st.columns(3)
if t_c1.button("2 MIN"): 
    st.session_state.finish_time = datetime.now() + timedelta(seconds=120)
    st.session_state.notified = False
if t_c2.button("3 MIN"): 
    st.session_state.finish_time = datetime.now() + timedelta(seconds=180)
    st.session_state.notified = False
if t_c3.button("RESET"): 
    st.session_state.finish_time = None

if st.session_state.finish_time:
    rem = (st.session_state.finish_time - datetime.now()).total_seconds()
    if rem > 0:
        m, s = divmod(int(rem), 60)
        st.metric("Siguiente serie en...", f"{m:02d}:{s:02d}")
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 ¡A ENTRENAR! 🚨")
        if not st.session_state.notified:
            st.audio("https://www.soundjay.com/buttons/sounds/button-3.mp3", autoplay=True)
            enviar_notificacion(f"🔔 ¡Descanso terminado! Te toca: {ejercicio_sel}")
            st.session_state.notified = True
            st.balloons()
