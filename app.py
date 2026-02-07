import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.express as px

# --- CONEXIÓN ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Abre el archivo y la hoja única
    ss = client.open("Entrenamientos_RayPeat")
    try:
        return ss.worksheet("Logs_Entrenamiento")
    except gspread.exceptions.WorksheetNotFound:
        # Si no existe, la crea con los encabezados
        ws = ss.add_worksheet(title="Logs_Entrenamiento", rows="1000", cols="10")
        ws.append_row(["Fecha", "Tipo Entrenamiento", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"])
        return ws

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="centered")

st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; text-align: left; padding-left: 15px; height: 50px; }
    .fase-box { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px; }
    .muscle-label { color: #FF4B4B; font-size: 0.85em; font-weight: bold; }
    .goal-label { color: #666; font-size: 0.8em; }
    </style>
    """, unsafe_allow_html=True)

# --- RUTINA CONFIG ---
config_rutina = {
    "Espalda-biceps": {
        "Pull Up (Weighted)": (3, "Espalda", "13"),
        "Chin Up (Weighted)": (3, "Espalda/Bíceps", "13"),
        "Seated Cable Row": (3, "Espalda", "13"),
        "Bicep Curl (Barbell)": (4, "Bíceps", "13"),
        "Incline Curl": (3, "Bíceps", "13")
    },
    "Pecho-triceps-hombro": {
        "Triceps Dip": (3, "Pecho/Tríceps", "8/11"),
        "Chest Press": (3, "Pecho", "8"),
        "Shoulder Press": (3, "Hombro", "9"),
        "Lateral Raise": (4, "Hombro Lat.", "4"),
        "Triceps Extension": (3, "Tríceps", "11"),
        "Tríceps Unilateral": (2, "Tríceps", "11"),
        "Manguito rotador": (2, "Salud Hombro", "Frecuencia: Empuje")
    },
    "Pierna": {
        "Full Squat": (4, "Pierna/Metab.", "7"),
        "Zancada": (3, "Cuádriceps/Glúteo", "7"),
        "Lying Leg Curl": (3, "Isquios", "3"),
        "Seated Calf Raise": (4, "Gemelos", "7"),
        "Standing Calf Raise": (3, "Gemelos", "7")
    },
    "Tren superior": {
        "Pull Up": (2, "Espalda", "13"),
        "Incline Bench Press": (2, "Pecho", "8"),
        "Military Press": (3, "Hombro", "10"),
        "Seated Cable Row (Wide)": (3, "Espalda", "14"),
        "Preacher Curl": (3, "Bíceps", "13"),
        "Single Arm Triceps Pushdown": (3, "Tríceps", "11")
    }
}

# --- NAVEGACIÓN ---
tab_entreno, tab_graficas = st.tabs(["🏋️ Entrenar Hoy", "📈 Mi Evolución"])

ws = conectar_google_sheets()

with tab_entreno:
    FECHA_INICIO = datetime(2026, 2, 2) 
    semana_actual = ((datetime.now() - FECHA_INICIO).days // 7) + 1
    fase = "MES 1: ADAPTACIÓN" if semana_actual <= 4 else ("MES 2: SOBRECARGA" if semana_actual <= 8 else "MES 3: INTENSIDAD")
    st.markdown(f"<div class='fase-box'><strong>Semana {semana_actual}</strong> | {fase}</div>", unsafe_allow_html=True)

    dia_sel = st.selectbox("Día de entrenamiento", list(config_rutina.keys()))
    
    # Manejo de datos: Leemos todo de la hoja única
    data = ws.get_all_records()
    df_all = pd.DataFrame(data) if data else pd.DataFrame(columns=["Fecha", "Tipo Entrenamiento", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"])

    hoy_str = datetime.now().strftime("%d/%m/%Y")
    hechos_hoy = []
    if not df_all.empty:
        df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
        hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

    st.subheader(f"Plan: {dia_sel}")
    for ex in config_rutina[dia_sel]:
        s_obj, musculo, obj_sem = config_rutina[dia_sel][ex]
        is_done = ex in hechos_hoy
        if st.button(f"{'✅' if is_done else '⚪'} {ex} ({s_obj} series)", key=f"btn_{ex}"):
            st.session_state.ej_activo = ex

    if "ej_activo" in st.session_state and st.session_state.ej_activo in config_rutina[dia_sel]:
        ex_active = st.session_state.ej_activo
        info = config_rutina[dia_sel][ex_active]
        st.divider()
        st.markdown(f"### 📝 {ex_active}")
        st.markdown(f"<span class='muscle-label'>{info[1]}</span> | Vol. Semanal: <span class='goal-label'>{info[2]}</span>", unsafe_allow_html=True)
        
        # Historial previo (del mismo ejercicio en cualquier entrenamiento)
        if not df_all.empty:
            df_prev = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] != hoy_str)]
            if not df_prev.empty:
                last_date = df_prev['Fecha_Solo'].iloc[-1]
                with st.expander(f"Ver historial ({last_date})"):
                    for _, r in df_prev[df_prev['Fecha_Solo'] == last_date].iterrows():
                        st.write(f"S{r['Serie']}: {r['Peso']}kg x {r['Repeticiones']}")

        # Formulario registro
        df_hoy_ex = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] == hoy_str)] if not df_all.empty else pd.DataFrame()
        c1, c2, c3 = st.columns([1, 2, 2])
        s_n = c1.number_input("Serie", value=len(df_hoy_ex)+1)
        p_n = c2.number_input("Kg", value=float(df_hoy_ex.iloc[-1]['Peso']) if not df_hoy_ex.empty else 0.0, step=0.5)
        r_n = c3.number_input("Reps", value=10)
        
        if st.button("💾 GUARDAR SERIE"):
            # AÑADIMOS 'dia_sel' como la columna de 'Tipo Entrenamiento'
            ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), dia_sel, ex_active, s_n, r_n, p_n, 8, ""])
            st.toast("¡Serie Guardada!")
            time.sleep(1)
            st.rerun()

    # Cronómetro
    st.divider()
    if "end_t" not in st.session_state: st.session_state.end_t = None
    cols_t = st.columns(3)
    if cols_t[0].button("2 MIN"): st.session_state.end_t = datetime.now() + timedelta(seconds=120)
    if cols_t[1].button("3 MIN"): st.session_state.end_t = datetime.now() + timedelta(seconds=180)
    if cols_t[2].button("RESET"): st.session_state.end_t = None
    
    if st.session_state.end_t:
        diff = (st.session_state.end_t - datetime.now()).total_seconds()
        if diff > 0:
            st.metric("Descanso", f"{int(diff//60):02d}:{int(diff%60):02d}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("🚨 ¡DALE A LA SIGUIENTE!")

with tab_graficas:
    st.subheader("Análisis de Progreso")
    # Los datos ya están cargados en df_all
    if not df_all.empty:
        # Filtro por tipo de entrenamiento para que sea fácil buscar el ejercicio
        dia_graf = st.selectbox("Filtrar por Rutina", list(config_rutina.keys()), key="graf_dia")
        
        ejercicios_disponibles = df_all[df_all['Tipo Entrenamiento'] == dia_graf]['Ejercicio'].unique()
        
        if len(ejercicios_disponibles) > 0:
            ex_graf = st.selectbox("Ejercicio", ejercicios_disponibles, key="graf_ex")
            df_ex = df_all[df_all['Ejercicio'] == ex_graf].copy()
            
            df_ex['Fecha_DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M")
            df_ex['1RM_Est'] = df_ex['Peso'] * (1 + df_ex['Repeticiones'] / 30)
            df_daily = df_ex.groupby(df_ex['Fecha_DT'].dt.date).agg({'Peso': 'max', '1RM_Est': 'max'}).reset_index()

            config_mobile = {'staticPlot': False, 'scrollZoom': False, 'displayModeBar': False}

            fig_peso = px.line(df_daily, x='Fecha_DT', y='Peso', title="Evolución Peso Máximo", markers=True)
            fig_peso.update_xaxes(fixedrange=True)
            fig_peso.update_yaxes(fixedrange=True)
            st.plotly_chart(fig_peso, use_container_width=True, config=config_mobile)

            fig_fuerza = px.line(df_daily, x='Fecha_DT', y='1RM_Est', title="Fuerza Estimada (1RM)", markers=True)
            fig_fuerza.update_traces(line_color='red')
            fig_fuerza.update_xaxes(fixedrange=True)
            fig_fuerza.update_yaxes(fixedrange=True)
            st.plotly_chart(fig_fuerza, use_container_width=True, config=config_mobile)
        else:
            st.info("No hay datos registrados aún para esta rutina.")
    else:
        st.warning("Registra series para ver tu evolución.")
