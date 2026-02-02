import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.express as px # Usaremos plotly para gráficas interactivas

# --- CONEXIÓN ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="📈", layout="centered")

st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; }
    .fase-box { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 20px; }
    .muscle-tag { font-size: 0.8em; color: #ff4b4b; font-weight: bold; background: #ffebeb; padding: 2px 8px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- RUTINA ---
rutina_detallada = {
    "Espalda-biceps": ["Pull Up (Weighted)", "Chin Up (Weighted)", "Seated Cable Row", "Bicep Curl (Barbell)", "Incline Curl"],
    "Pecho-triceps-hombro": ["Shoulder Press", "Chest Press", "Triceps Dip", "Lateral Raise", "Triceps Extension", "Tríceps Unilateral"],
    "Pierna": ["Full Squat", "Zancada", "Lying Leg Curl", "Seated Calf Raise", "Standing Calf Raise"],
    "Tren superior": ["Incline Bench Press", "Seated Cable Row (Wide)", "Lateral Raise", "Preacher Curl", "Single Arm Triceps Pushdown"]
}

# --- NAVEGACIÓN POR PESTAÑAS ---
tab_entreno, tab_graficas = st.tabs(["🏋️ Entrenar Hoy", "📈 Mi Evolución"])

# --- CARGA DE DATOS GENERAL ---
ss = conectar_google_sheets()

with tab_entreno:
    # Planificación
    FECHA_INICIO = datetime(2026, 2, 2) 
    semana_actual = ((datetime.now() - FECHA_INICIO).days // 7) + 1
    fase = "MES 1: ADAPTACIÓN" if semana_actual <= 4 else ("MES 2: SOBRECARGA" if semana_actual <= 8 else "MES 3: INTENSIDAD")
    st.markdown(f"<div class='fase-box'><strong>Semana {semana_actual}</strong> | {fase}</div>", unsafe_allow_html=True)

    dia_sel = st.selectbox("Día de entrenamiento", list(rutina_detallada.keys()))
    ws = ss.worksheet(dia_sel)
    df_all = pd.DataFrame(ws.get_all_records())
    
    # Checklist de hoy
    hoy_str = datetime.now().strftime("%d/%m/%Y")
    hechos_hoy = []
    if not df_all.empty:
        df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
        hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

    st.subheader("Lista de Ejercicios")
    for ex in rutina_detallada[dia_sel]:
        if st.button(f"{'✅' if ex in hechos_hoy else '⚪'} {ex}", key=f"btn_{ex}"):
            st.session_state.ej_activo = ex

    if "ej_activo" in st.session_state and st.session_state.ej_activo in rutina_detallada[dia_sel]:
        ex_active = st.session_state.ej_activo
        st.divider()
        st.markdown(f"### 📝 {ex_active}")
        
        # Referencia anterior
        df_prev = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] != hoy_str)]
        if not df_prev.empty:
            last_date = df_prev['Fecha_Solo'].iloc[-1]
            with st.expander(f"Ver marca anterior ({last_date})"):
                for _, r in df_prev[df_prev['Fecha_Solo'] == last_date].iterrows():
                    st.write(f"S{r['Serie']}: {r['Peso']}kg x {r['Repeticiones']}")

        # Registro
        df_hoy_ex = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] == hoy_str)]
        c1, c2, c3 = st.columns([1, 2, 2])
        s_n = c1.number_input("S", value=len(df_hoy_ex)+1)
        p_n = c2.number_input("Kg", value=float(df_hoy_ex.iloc[-1]['Peso']) if not df_hoy_ex.empty else 0.0, step=0.5)
        r_n = c3.number_input("Reps", value=10)
        
        if st.button("💾 GUARDAR SERIE"):
            ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), ex_active, s_n, r_n, p_n, 8, ""])
            st.rerun()

    # Cronómetro (al final del entreno)
    st.divider()
    if "end_t" not in st.session_state: st.session_state.end_t = None
    cols_t = st.columns(3)
    if cols_t[0].button("2 MIN"): st.session_state.end_t = datetime.now() + timedelta(seconds=120)
    if cols_t[1].button("3 MIN"): st.session_state.end_t = datetime.now() + timedelta(seconds=180)
    if cols_t[2].button("RESET"): st.session_state.end_t = None
    
    if st.session_state.end_t:
        diff = (st.session_state.end_t - datetime.now()).total_seconds()
        if diff > 0:
            st.metric("Descansando...", f"{int(diff//60):02d}:{int(diff%60):02d}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("🚨 ¡A POR LA SIGUIENTE!")

with tab_graficas:
    st.subheader("Análisis de Progreso")
    dia_graf = st.selectbox("Selecciona grupo para analizar", list(rutina_detallada.keys()), key="graf_dia")
    ws_g = ss.worksheet(dia_graf)
    df_g = pd.DataFrame(ws_g.get_all_records())

    if not df_g.empty:
        ex_graf = st.selectbox("Ejercicio", rutina_detallada[dia_graf], key="graf_ex")
        df_ex = df_g[df_g['Ejercicio'] == ex_graf].copy()
        
        if not df_ex.empty:
            # Limpiar datos para la gráfica
            df_ex['Fecha_DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M")
            # Calcular 1RM Estimado (Fórmula de Epley: Peso * (1 + Reps/30))
            df_ex['1RM_Est'] = df_ex['Peso'] * (1 + df_ex['Repeticiones'] / 30)
            
            # Agrupar por fecha para ver el máximo de cada día
            df_daily = df_ex.groupby(df_ex['Fecha_DT'].dt.date).agg({'Peso': 'max', '1RM_Est': 'max'}).reset_index()

            # Gráfica de Peso Máximo
            fig_peso = px.line(df_daily, x='Fecha_DT', y='Peso', title=f"Evolución Peso Máximo (kg) - {ex_graf}", markers=True)
            st.plotly_chart(fig_peso, use_container_width=True)

            # Gráfica de Fuerza Estimada (1RM)
            fig_fuerza = px.line(df_daily, x='Fecha_DT', y='1RM_Est', title=f"Evolución Fuerza Estimada (1RM) - {ex_graf}", markers=True)
            fig_fuerza.update_traces(line_color='red')
            st.plotly_chart(fig_fuerza, use_container_width=True)
            
            st.info("💡 El 1RM estimado te indica si estás ganando fuerza real, incluso si bajas repeticiones pero subes peso.")
        else:
            st.warning("Aún no hay datos para este ejercicio.")
    else:
        st.warning("No hay datos en esta categoría.")
