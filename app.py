import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
st.set_page_config(page_title="Bio-Log Live", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 50px; border-radius: 12px; }
    .done { color: #28a745; font-weight: bold; }
    .pending { color: #6c757d; }
    .last-session-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- RUTINA ---
rutina = {
    "Espalda-biceps": ["Pull Up (Weighted)", "Chin Up (Weighted)", "Seated Cable Row", "Bicep Curl (Barbell)", "Incline Curl"],
    "Pecho-triceps-hombro": ["Shoulder Press", "Chest Press", "Triceps Dip", "Lateral Raise", "Triceps Extension", "Tríceps Unilateral"],
    "Pierna": ["Full Squat", "Zancada", "Lying Leg Curl", "Seated Calf Raise", "Standing Calf Raise"],
    "Tren superior": ["Incline Bench Press", "Seated Cable Row (Wide)", "Lateral Raise", "Preacher Curl", "Single Arm Triceps Pushdown"]
}

# --- LÓGICA DE DATOS ---
ss = conectar_google_sheets()
dia_actual = st.selectbox("Selecciona Sesión", list(rutina.keys()))
ws = ss.worksheet(dia_actual)
df_all = pd.DataFrame(ws.get_all_records())

# Filtrar datos de HOY
hoy_str = datetime.now().strftime("%d/%m/%Y")
if not df_all.empty:
    # Aseguramos que la columna Fecha sea string para comparar
    df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
    ejercicios_hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()
else:
    ejercicios_hechos_hoy = []

# --- 1. ESTADO DEL ENTRENAMIENTO ---
st.subheader("Progreso de la Sesión")
cols = st.columns(len(rutina[dia_actual]))
for i, ex in enumerate(rutina[dia_actual]):
    is_done = ex in ejercicios_hechos_hoy
    label = f"✅ {ex}" if is_done else f"⚪ {ex}"
    color = "done" if is_done else "pending"
    st.markdown(f"<div class='{color}'>{label}</div>", unsafe_allow_html=True)

st.divider()

# --- 2. SELECCIÓN Y REFERENCIA HISTÓRICA ---
ejercicio_sel = st.selectbox("Ejercicio a registrar", rutina[dia_actual])

# Buscar datos de la ÚLTIMA VEZ (excluyendo hoy)
if not df_all.empty:
    df_prev = df_all[(df_all['Ejercicio'] == ejercicio_sel) & (df_all['Fecha_Solo'] != hoy_str)]
    if not df_prev.empty:
        ultima_fecha = df_prev['Fecha'].iloc[-1].split(' ')[0]
        st.markdown(f"""
        <div class='last-session-box'>
            <p style='margin:0; font-size:0.9em; color:#555;'>📅 Última vez: {ultima_fecha}</p>
            <h4 style='margin:5px 0;'>Marcas a batir:</h4>
        """, unsafe_allow_html=True)
        
        # Mostrar series de la última vez
        last_data = df_prev[df_prev['Fecha_Solo'] == df_prev['Fecha_Solo'].iloc[-1]]
        for _, row in last_data.iterrows():
            st.write(f"Serie {row['Serie']}: **{row['Peso']} kg** x {row['Repeticiones']} reps")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Primer registro para este ejercicio. ¡Establece tu base!")

# --- 3. REGISTRO DE SERIE ---
# Sugerir siguiente serie según hoy
df_hoy = df_all[(df_all['Ejercicio'] == ejercicio_sel) & (df_all['Fecha_Solo'] == hoy_str)]
siguiente_serie = len(df_hoy) + 1
peso_sugerido = 0.0 if df_hoy.empty else float(df_hoy.iloc[-1]['Peso'])

with st.container():
    c1, c2, c3 = st.columns([1, 2, 2])
    n_serie = c1.number_input("Serie", value=siguiente_serie, step=1)
    n_peso = c2.number_input("Peso (kg)", value=peso_sugerido, step=0.5)
    n_reps = c3.number_input("Reps", value=10, step=1)
    
    boton_save = st.button("💾 GUARDAR SERIE")

    if boton_save:
        fecha_completa = datetime.now().strftime("%d/%m/%Y %H:%M")
        ws.append_row([fecha_completa, ejercicio_sel, n_serie, n_reps, n_peso, 8, ""])
        st.success(f"Guardado: {n_peso}kg x {n_reps}")
        time.sleep(1)
        st.rerun()

# --- 4. CRONÓMETRO RÁPIDO ---
st.divider()
st.subheader("⏱️ Descanso")
t_col1, t_col2 = st.columns(2)
timer_req = 0
if t_col1.button("⏱️ 2 MIN"): timer_req = 120
if t_col2.button("⏱️ 3 MIN"): timer_req = 180

if timer_req > 0:
    ph = st.empty()
    for t in range(timer_req, -1, -1):
        m, s = divmod(t, 60)
        ph.metric("Siguiente serie en...", f"{m:02d}:{s:02d}")
        time.sleep(1)
    st.audio("https://www.soundjay.com/buttons/sounds/button-3.mp3") # Sonido opcional
    ph.success("¡VAMOS!")

