import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="centered")

st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; margin-bottom: 5px; }
    .exercise-card { padding: 15px; border-radius: 12px; border: 1px solid #ddd; background-color: #f9f9f9; margin-bottom: 10px; }
    .muscle-label { color: #FF4B4B; font-size: 0.85em; font-weight: bold; }
    .goal-label { color: #666; font-size: 0.8em; }
    .fase-box { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px; }
    .done-btn { border-left: 8px solid #28a745 !important; background-color: #f0fff4 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DEFINICIÓN DE RUTINA OPTIMIZADA (4 DÍAS) ---
# Estructura: "Día": {"Ejercicio": (Series, Músculo, Objetivo Semanal)}
config_rutina = {
    "Espalda-biceps": {
        "Pull Up (Weighted)": (3, "Espalda", "11 series/sem"),
        "Chin Up (Weighted)": (2, "Espalda/Bíceps", "11 series/sem"),
        "Seated Cable Row": (3, "Espalda", "11 series/sem"),
        "Bicep Curl (Barbell)": (4, "Bíceps", "12 series/sem"),
        "Incline Curl": (3, "Bíceps", "12 series/sem")
    },
    "Pecho-triceps-hombro": {
        "Shoulder Press": (3, "Hombro", "11 series/sem"),
        "Chest Press": (3, "Pecho", "9 series/sem"),
        "Triceps Dip": (3, "Tríceps/Pecho", "11 series/sem"),
        "Lateral Raise": (4, "Hombro", "11 series/sem"),
        "Triceps Extension": (3, "Tríceps", "11 series/sem"),
        "Tríceps Unilateral": (2, "Tríceps", "11 series/sem")
    },
    "Pierna": {
        "Full Squat": (4, "Pierna/Metabolismo", "10 series/sem"),
        "Zancada": (3, "Pierna/Glúteo", "10 series/sem"),
        "Lying Leg Curl": (3, "Isquios", "10 series/sem"),
        "Seated Calf Raise": (4, "Gemelos", "13 series/sem"),
        "Standing Calf Raise": (3, "Gemelos", "13 series/sem")
    },
    "Tren superior": {
        "Incline Bench Press": (3, "Pecho", "9 series/sem"),
        "Seated Cable Row (Wide)": (3, "Espalda", "11 series/sem"),
        "Lateral Raise": (4, "Hombro", "11 series/sem"),
        "Preacher Curl": (3, "Bíceps", "12 series/sem"),
        "Single Arm Triceps Pushdown": (3, "Tríceps", "11 series/sem"),
        "Standing Calf Raise (Extra)": (3, "Gemelos", "13 series/sem")
    }
}

# --- INICIO DE APP ---
st.title("🧬 Bio-Hypertrophy Log")

# Planificación 3 Meses
FECHA_INICIO = datetime(2026, 2, 2) 
semana_actual = ((datetime.now() - FECHA_INICIO).days // 7) + 1
fase = "MES 1: ADAPTACIÓN" if semana_actual <= 4 else ("MES 2: SOBRECARGA" if semana_actual <= 8 else "MES 3: INTENSIDAD")

st.markdown(f"<div class='fase-box'><strong>Semana {semana_actual}</strong> | {fase}</div>", unsafe_allow_html=True)

# Selección de día
dia_sel = st.selectbox("Día de entrenamiento", list(config_rutina.keys()))

# Cargar datos de hoy
ss = conectar_google_sheets()
ws = ss.worksheet(dia_sel)
df_all = pd.DataFrame(ws.get_all_records())
hoy_str = datetime.now().strftime("%d/%m/%Y")

hechos_hoy = []
if not df_all.empty:
    df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
    hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

# --- LISTA DE EJERCICIOS ---
st.subheader("Plan del Día")
ejercicio_activo = st.session_state.get("ej_activo", None)

for ex in config_rutina[dia_sel]:
    series, musculo, objetivo = config_rutina[dia_sel][ex]
    is_done = ex in hechos_hoy
    
    # Botón de estilo lista
    btn_label = f"{'✅' if is_done else '⚪'} {ex} ({series} series)"
    if st.button(btn_label, key=ex, help=f"Músculo: {musculo}", use_container_width=True):
        st.session_state.ej_activo = ex
        st.rerun()

st.divider()

# --- PANEL DE REGISTRO ---
if ejercicio_activo and ejercicio_activo in config_rutina[dia_sel]:
    ex_info = config_rutina[dia_sel][ejercicio_activo]
    st.markdown(f"### 📝 {ejercicio_activo}")
    st.markdown(f"<span class='muscle-label'>{ex_info[1]}</span> | <span class='goal-label'>Meta: {ex_info[2]}</span>", unsafe_allow_html=True)

    # Mostrar marcas anteriores
    if not df_all.empty:
        df_prev = df_all[(df_all['Ejercicio'] == ejercicio_activo) & (df_all['Fecha_Solo'] != hoy_str)]
        if not df_prev.empty:
            last_session = df_prev['Fecha_Solo'].iloc[-1]
            with st.expander(f"📖 Ver base anterior ({last_session})", expanded=True):
                df_last = df_prev[df_prev['Fecha_Solo'] == last_session]
                for _, r in df_last.iterrows():
                    st.write(f"S{r['Serie']}: **{r['Peso']} kg** x {r['Repeticiones']}")

    # Formulario rápido
    df_hoy = df_all[(df_all['Ejercicio'] == ejercicio_activo) & (df_all['Fecha_Solo'] == hoy_str)]
    next_serie = len(df_hoy) + 1
    peso_anterior = 0.0 if df_hoy.empty else float(df_hoy.iloc[-1]['Peso'])

    with st.container():
        c1, c2, c3 = st.columns([1, 2, 2])
        val_s = c1.number_input("Serie", value=next_serie)
        val_p = c2.number_input("Kg", value=peso_anterior, step=0.5)
        val_r = c3.number_input("Reps", value=10)
        
        if st.button("💾 GUARDAR SERIE"):
            ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), ejercicio_activo, val_s, val_r, val_p, 8, ""])
            st.toast(f"Guardado: {ejercicio_activo} S{val_s}")
            time.sleep(1)
            st.rerun()

# --- CRONÓMETRO ---
st.divider()
if "finish" not in st.session_state: st.session_state.finish = None

st.subheader("⏱️ Descanso")
t1, t2, t3 = st.columns(3)
if t1.button("2 MIN"): st.session_state.finish = datetime.now() + timedelta(seconds=120)
if t2.button("3 MIN"): st.session_state.finish = datetime.now() + timedelta(seconds=180)
if t3.button("RESET"): st.session_state.finish = None

if st.session_state.finish:
    diff = (st.session_state.finish - datetime.now()).total_seconds()
    if diff > 0:
        m, s = divmod(int(diff), 60)
        st.metric("Descansando...", f"{m:02d}:{s:02d}")
        time.sleep(1)
        st.rerun()
    else:
        st.error("🚨 ¡TIEMPO CUMPLIDO!")
        st.session_state.finish = None
