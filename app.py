import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time

# 1. FUNCIÓN DE CONEXIÓN
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

# 2. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="Bio-Log Pro", page_icon="🔋", layout="centered")

# Estilo para botones y diseño móvil
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 5px; }
    div.stButton > button:first-child { background-color: #FF4B4B; color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔋 Bio-Log Pro")

# 3. DEFINICIÓN DE LA RUTINA Y CALENDARIO
rutina = {
    "Espalda-biceps": ["Pull Up (Weighted)", "Chin Up (Weighted)", "Seated Cable Row", "Bicep Curl (Barbell)", "Incline Curl"],
    "Pecho-triceps-hombro": ["Shoulder Press", "Chest Press", "Triceps Dip", "Lateral Raise", "Triceps Extension", "Tríceps Unilateral"],
    "Pierna": ["Full Squat", "Zancada", "Lying Leg Curl", "Seated Calf Raise", "Standing Calf Raise"],
    "Tren superior": ["Incline Bench Press", "Seated Cable Row (Wide)", "Lateral Raise", "Preacher Curl", "Single Arm Triceps Pushdown"]
}

programacion = {
    "Monday": "Espalda-biceps",
    "Tuesday": "Pecho-triceps-hombro",
    "Thursday": "Pierna",
    "Friday": "Tren superior"
}

# --- PESTAÑAS PRINCIPALES ---
tab_registro, tab_timer, tab_progreso, tab_calendario = st.tabs(["📝 Registro", "⏱️ Descanso", "📈 Progreso", "📅 Agenda"])

# --- TAB 1: REGISTRO ---
with tab_registro:
    # Sugerir día según calendario
    dia_actual_eng = datetime.now().strftime("%A")
    sugerencia = programacion.get(dia_actual_eng, "Espalda-biceps")
    
    dia_sel = st.selectbox("Sesión", list(rutina.keys()), index=list(rutina.keys()).index(sugerencia))
    ejercicio_sel = st.selectbox("Ejercicio", rutina[dia_sel])

    # Mostrar PR (Récord Personal) si existe
    try:
        ss = conectar_google_sheets()
        ws = ss.worksheet(dia_sel)
        df_hist = pd.DataFrame(ws.get_all_records())
        if not df_hist.empty:
            pr_val = df_hist[df_hist['Ejercicio'] == ejercicio_sel]['Peso'].max()
            st.info(f"🏆 Tu Récord Personal en este ejercicio: **{pr_val} kg**")
    except:
        pass

    with st.form("registro_serie"):
        c1, c2 = st.columns(2)
        peso = c1.number_input("Peso (kg)", step=0.5, format="%.2f")
        serie = c1.number_input("Serie nº", min_value=1, step=1)
        reps = c2.number_input("Reps", min_value=1, step=1)
        rpe = c2.select_slider("Esfuerzo (RPE)", options=range(1, 11), value=8)
        
        # Opciones Bioenergéticas (Peat)
        with st.expander("🩺 Datos Metabólicos (Opcional)"):
            pulso = st.number_input("Pulso (BPM)", min_value=0)
            temp = st.number_input("Temp (°C)", min_value=0.0, format="%.1f")
        
        notas = st.text_input("Notas de la serie")
        save = st.form_submit_button("GUARDAR SERIE")

        if save:
            try:
                ss = conectar_google_sheets()
                ws = ss.worksheet(dia_sel)
                fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
                ws.append_row([fecha, ejercicio_sel, serie, reps, peso, rpe, notas, pulso, temp])
                st.success("Serie guardada correctamente")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: CRONÓMETRO DE DESCANSO ---
with tab_timer:
    st.subheader("Tiempo de Recuperación")
    minutos = st.number_input("Minutos de descanso", 1, 5, 2)
    segundos_totales = minutos * 60
    
    if st.button("🚀 INICIAR DESCANSO"):
        ph = st.empty()
        for i in range(segundos_totales, 0, -1):
            mm, ss = divmod(i, 60)
            ph.metric("Tiempo restante", f"{mm:02d}:{ss:02d}")
            time.sleep(1)
        ph.success("🔔 ¡A ENTRENAR! Descanso terminado.")
        st.write("Recuerda: Un descanso largo (2-3 min) reduce el cortisol y el lactato.")

# --- TAB 3: PROGRESO ---
with tab_progreso:
    st.subheader("Tu Evolución")
    try:
        ss = conectar_google_sheets()
        ws = ss.worksheet(dia_sel)
        df_prog = pd.DataFrame(ws.get_all_records())
        if not df_prog.empty:
            df_ex = df_prog[df_prog['Ejercicio'] == ejercicio_sel]
            if not df_ex.empty:
                st.line_chart(df_ex.set_index('Fecha')['Peso'])
                st.write("Últimas series:")
                st.dataframe(df_ex.tail(5))
    except:
        st.warning("No hay datos para graficar aún.")

# --- TAB 4: CALENDARIO ---
with tab_calendario:
    st.subheader("Próximos 7 días")
    hoy = datetime.now()
    for i in range(7):
        fecha_futura = hoy + timedelta(days=i)
        dia_nombre = fecha_futura.strftime("%A")
        entreno = programacion.get(dia_nombre, "🟢 Descanso / Movimiento suave")
        
        col_fecha, col_tipo = st.columns([1, 2])
        col_fecha.write(fecha_futura.strftime("%d %b"))
        col_tipo.write(f"**{entreno}**")
