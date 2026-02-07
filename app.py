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
    return client.open("Entrenamientos_RayPeat")

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

# --- RUTINA ACTUALIZADA (ORDEN ÓPTIMO) ---
# --- RUTINA ACTUALIZADA (ORDEN ÓPTIMO) ---
# --- RUTINA ACTUALIZADA (CON PRESS INCLINADO) ---
config_rutina = {
    "Espalda-biceps": {
        "Pull Up (Weighted)": (3, "Espalda", "Total Semanal: 13"),
        "Chin Up (Weighted)": (3, "Espalda/Bíceps", "Total Semanal: 13"),
        "Seated Cable Row": (3, "Espalda", "Total Semanal: 13"),
        "Bicep Curl (Barbell)": (4, "Bíceps", "Total Semanal: 13"),
        "Incline Curl": (3, "Bíceps", "Total Semanal: 13")
    },
    "Pecho-triceps-hombro": {
        "Triceps Dip": (3, "Pecho/Tríceps", "Total Semanal: 8/11"),
        "Chest Press": (3, "Pecho", "Total Semanal: 8"),
        "Shoulder Press": (3, "Hombro", "Total Semanal: 9"),
        "Lateral Raise": (4, "Hombro Lat.", "Total Semanal: 4"),
        "Triceps Extension": (3, "Tríceps", "Total Semanal: 11"),
        "Tríceps Unilateral": (2, "Tríceps", "Total Semanal: 11"),
        "Manguito rotador": (2, "Salud Hombro", "Frecuencia: Cada sesión empuje")
    },
    "Pierna": {
        "Full Squat": (4, "Pierna/Metab.", "Total Semanal: 7"),
        "Zancada": (3, "Cuádriceps/Glúteo", "Total Semanal: 7"),
        "Lying Leg Curl": (3, "Isquios", "Total Semanal: 3"),
        "Seated Calf Raise": (4, "Gemelos", "Total Semanal: 7"),
        "Standing Calf Raise": (3, "Gemelos", "Total Semanal: 7")
    },
    "Tren superior": {
        "Pull Up": (2, "Espalda", "Total Semanal: 13"),
        "Incline Bench Press": (2, "Pecho", "Total Semanal: 8"),
        "Military Press": (2, "Hombro", "Total Semanal: 9"),
        "Seated Cable Row (Wide)": (2, "Espalda", "Total Semanal: 13"),
        "Preacher Curl": (3, "Bíceps", "Total Semanal: 13"),
        "Single Arm Triceps Pushdown": (3, "Tríceps", "Total Semanal: 11")
    }
}

# --- NAVEGACIÓN ---
tab_entreno, tab_graficas = st.tabs(["🏋️ Entrenar Hoy", "📈 Mi Evolución"])

ss = conectar_google_sheets()

with tab_entreno:
    # Planificación Automática
    FECHA_INICIO = datetime(2026, 2, 2) 
    semana_actual = ((datetime.now() - FECHA_INICIO).days // 7) + 1
    fase = "MES 1: ADAPTACIÓN" if semana_actual <= 4 else ("MES 2: SOBRECARGA" if semana_actual <= 8 else "MES 3: INTENSIDAD")
    st.markdown(f"<div class='fase-box'><strong>Semana {semana_actual}</strong> | {fase}</div>", unsafe_allow_html=True)

    dia_sel = st.selectbox("Día de entrenamiento", list(config_rutina.keys()))
    ws = ss.worksheet(dia_sel)
    
    # Manejo de datos
    data = ws.get_all_records()
    headers = ["Fecha", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"]
    if not data:
        ws.insert_row(headers, 1)
        df_all = pd.DataFrame(columns=headers)
    else:
        df_all = pd.DataFrame(data)

    hoy_str = datetime.now().strftime("%d/%m/%Y")
    hechos_hoy = []
    if 'Ejercicio' in df_all.columns and not df_all.empty:
        df_all['Fecha_Solo'] = df_all['Fecha'].apply(lambda x: str(x).split(' ')[0])
        hechos_hoy = df_all[df_all['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

    st.subheader("Plan del Día")
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
        st.markdown(f"<span class='muscle-label'>{info[1]}</span> | <span class='goal-label'>{info[2]}</span>", unsafe_allow_html=True)
        
        # Historial previo
        if 'Ejercicio' in df_all.columns and not df_all.empty:
            df_prev = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] != hoy_str)]
            if not df_prev.empty:
                last_date = df_prev['Fecha_Solo'].iloc[-1]
                with st.expander(f"Ver base anterior ({last_date})"):
                    for _, r in df_prev[df_prev['Fecha_Solo'] == last_date].iterrows():
                        st.write(f"S{r['Serie']}: {r['Peso']}kg x {r['Repeticiones']}")

        # Formulario registro
        df_hoy_ex = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] == hoy_str)] if not df_all.empty else pd.DataFrame()
        c1, c2, c3 = st.columns([1, 2, 2])
        s_n = c1.number_input("Serie", value=len(df_hoy_ex)+1)
        p_n = c2.number_input("Kg", value=float(df_hoy_ex.iloc[-1]['Peso']) if not df_hoy_ex.empty else 0.0, step=0.5)
        r_n = c3.number_input("Reps", value=10)
        
        if st.button("💾 GUARDAR SERIE"):
            ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), ex_active, s_n, r_n, p_n, 8, ""])
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

# ... (Todo el código anterior de conexión y rutina se mantiene igual) ...

with tab_graficas:
    st.subheader("Análisis de Progreso")
    dia_graf = st.selectbox("Grupo", list(config_rutina.keys()), key="graf_dia")
    ws_g = ss.worksheet(dia_graf)
    df_g = pd.DataFrame(ws_g.get_all_records())

    if not df_g.empty and 'Ejercicio' in df_g.columns:
        ex_graf = st.selectbox("Ejercicio", config_rutina[dia_graf].keys(), key="graf_ex")
        df_ex = df_g[df_g['Ejercicio'] == ex_graf].copy()
        
        if not df_ex.empty:
            df_ex['Fecha_DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M")
            df_ex['1RM_Est'] = df_ex['Peso'] * (1 + df_ex['Repeticiones'] / 30)
            df_daily = df_ex.groupby(df_ex['Fecha_DT'].dt.date).agg({'Peso': 'max', '1RM_Est': 'max'}).reset_index()

            # --- CONFIGURACIÓN DE BLOQUEO (MOBILE FRIENDLY) ---
            # Bloqueamos el zoom y el pan (movimiento) para que no moleste al hacer scroll
            config_mobile = {
                'staticPlot': False,  # Permite ver datos al tocar, pero no mover la gráfica
                'scrollZoom': False,
                'displayModeBar': False, # Escondemos la barra de herramientas que molesta
                'doubleClick': 'reset'
            }

            # Gráfica de Peso Máximo
            fig_peso = px.line(df_daily, x='Fecha_DT', y='Peso', title="Evolución Peso Máximo", markers=True)
            fig_peso.update_xaxes(fixedrange=True) # BLOQUEO EJE X
            fig_peso.update_yaxes(fixedrange=True) # BLOQUEO EJE Y
            st.plotly_chart(fig_peso, use_container_width=True, config=config_mobile)

            # Gráfica de 1RM
            fig_fuerza = px.line(df_daily, x='Fecha_DT', y='1RM_Est', title="Fuerza Estimada (1RM)", markers=True)
            fig_fuerza.update_traces(line_color='red')
            fig_fuerza.update_xaxes(fixedrange=True) # BLOQUEO EJE X
            fig_fuerza.update_yaxes(fixedrange=True) # BLOQUEO EJE Y
            st.plotly_chart(fig_fuerza, use_container_width=True, config=config_mobile)
            
            st.caption("ℹ️ El zoom está desactivado para facilitar la navegación en el móvil.")
        else:
            st.info("Sin datos para este ejercicio.")
    else:
        st.warning("Registra series para ver tu evolución.")

