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
st.set_page_config(page_title="Gym Bio-Log", page_icon="💪", layout="centered")

# Estilo para móvil: botones grandes y menos espacios
st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 60px; font-size: 20px !important; border-radius: 12px; }
    .stNumberInput input { font-size: 20px !important; }
    div[data-testid="stMetricValue"] { font-size: 40px !important; color: #FF4B4B; }
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

tab_registro, tab_historial, tab_agenda = st.tabs(["🔥 ENTRENAR", "📊 PROGRESO", "📅 AGENDA"])

with tab_registro:
    # 1. Selección de ejercicio
    dia_actual = st.selectbox("Sesión", list(rutina.keys()))
    ejercicio_sel = st.selectbox("Ejercicio", rutina[dia_actual])
    
    # 2. Obtener datos previos para auto-rellenado
    ws = ss.worksheet(dia_actual)
    df_actual = pd.DataFrame(ws.get_all_records())
    
    # Sugerir siguiente serie y peso anterior
    ultima_serie = 1
    peso_sugerido = 0.0
    if not df_actual.empty:
        df_ej = df_actual[df_actual['Ejercicio'] == ejercicio_sel]
        if not df_ej.empty:
            ultima_serie = df_ej['Serie'].max() + 1
            peso_sugerido = float(df_ej.iloc[-1]['Peso'])

    # 3. Formulario intuitivo
    st.markdown("### Registrar Serie")
    with st.container():
        c1, c2 = st.columns(2)
        serie = c1.number_input("Serie nº", value=ultima_serie, step=1)
        peso = c2.number_input("Peso (kg)", value=peso_sugerido, step=0.5, format="%.2f")
        
        c3, c4 = st.columns(2)
        reps = c3.number_input("Repeticiones", value=10, step=1)
        rpe = c4.select_slider("RPE (Esfuerzo)", options=range(1,11), value=8)
        
    notas = st.text_input("Notas rápidas", placeholder="¿Cómo te has sentido?")

    if st.button("💾 GUARDAR SERIE"):
        try:
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
            ws.append_row([fecha, ejercicio_sel, serie, reps, peso, rpe, notas])
            st.toast(f"¡Serie {serie} guardada!", icon="✅")
            # Forzamos recarga para que el nº de serie se actualice solo
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    # 4. CRONÓMETRO INTEGRADO (Justo debajo del registro)
    st.divider()
    st.markdown("### ⏱️ Descanso Bioenergético")
    col_t1, col_t2, col_t3 = st.columns(3)
    
    # Botones rápidos de tiempo
    t_descanso = 0
    if col_t1.button("2 min"): t_descanso = 120
    if col_t2.button("3 min"): t_descanso = 180
    if col_t3.button("Personalizado"): t_descanso = 60

    if t_descanso > 0:
        placeholder = st.empty()
        for t in range(t_descanso, -1, -1):
            m, s = divmod(t, 60)
            placeholder.metric("Tiempo para la siguiente serie", f"{m:02d}:{s:02d}")
            time.sleep(1)
        placeholder.success("🔔 ¡DALE! Estás recuperado.")
        st.balloons()

with tab_historial:
    st.subheader("Tus últimas marcas")
    if not df_actual.empty:
        st.dataframe(df_actual[df_actual['Ejercicio'] == ejercicio_sel].tail(5), use_container_width=True)
        # Gráfica de peso
        df_plot = df_actual[df_actual['Ejercicio'] == ejercicio_sel]
        if not df_plot.empty:
            st.line_chart(df_plot, x='Fecha', y='Peso')

with tab_agenda:
    st.info("Plan de 3 meses: Frecuencia 2 en extremidades")
    st.write("**Lunes:** Espalda-bíceps")
    st.write("**Martes:** Pecho-tríceps-hombro")
    st.write("**Jueves:** Pierna")
    st.write("**Viernes:** Tren superior")
