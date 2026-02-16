import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.express as px

# 1. Función de seguridad con control de tiempo
def check_password():
    """Devuelve True si la contraseña es correcta y la sesión (90min) sigue activa."""
    
    # Definimos el tiempo de validez: 1 hora y 30 minutos
    TIEMPO_SESION = timedelta(hours=1, minutes=30)

    # Lógica para verificar contraseña
    def password_entered():
        """Revisa si la contraseña coincide y guarda la hora de inicio."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            # Guardamos el momento exacto del login
            st.session_state["login_time"] = datetime.now()
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # A. Comprobamos si ya hay una sesión iniciada
    if "password_correct" in st.session_state and st.session_state["password_correct"]:
        # Calculamos cuánto tiempo ha pasado
        if "login_time" in st.session_state:
            tiempo_transcurrido = datetime.now() - st.session_state["login_time"]
            
            # Si ha pasado más de 1.5 horas, cerramos la sesión
            if tiempo_transcurrido > TIEMPO_SESION:
                del st.session_state["password_correct"]
                del st.session_state["login_time"]
                st.error("⌛ Tu sesión de 90 minutos ha expirado. Ingresa de nuevo.")
                return False
            else:
                # Si estamos dentro del tiempo, todo OK
                return True
    
    # B. Si no hay sesión o falló la contraseña previa, pedimos input
    st.text_input("Introduce la contraseña para acceder", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Contraseña errónea")
        
    return False

# 2. BLOQUE PRINCIPAL (Todo lo que sigue tiene 4 espacios de sangría)
if check_password():
    
    # --- CONEXIÓN (Dentro del IF) ---
    def conectar_google_sheets():
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        # FIX: Limpiamos la clave para evitar el UnsupportedSubstrateError
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        ss = client.open("Entrenamientos_RayPeat")
        try:
            return ss.worksheet("Logs_Entrenamiento")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="Logs_Entrenamiento", rows="1000", cols="10")
            ws.append_row(["Fecha", "Tipo Entrenamiento", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"])
            return ws

    # --- CONFIGURACIÓN ---
    st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="centered")

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        .main { background-color: #0E1117; font-family: 'Outfit', sans-serif; }
        .fase-box {
            background: linear-gradient(135deg, #1e1e2f 0%, #0f0f1a 100%);
            color: #ffffff; padding: 24px; border-radius: 20px;
            border: 1px solid #3d3d5c; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            text-align: center; margin-bottom: 30px;
        }
        .stButton > button {
            background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d;
            border-radius: 12px; padding: 15px 20px; transition: all 0.2s ease-in-out;
            text-align: left; width: 100%; font-size: 16px; font-weight: 500;
        }
        .stButton > button:hover { border-color: #58a6ff; background-color: #1c2128; color: #58a6ff; transform: translateX(5px); }
        .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; }
        .muscle-label { background-color: rgba(88, 166, 255, 0.1); color: #58a6ff; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; border: 1px solid rgba(88, 166, 255, 0.3); }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)

    # --- RUTINA CONFIG ---
    config_rutina = {
        "Espalda-biceps": {
            "Pull Up (Weighted)": (3, "Espalda", "14"),
            "Chin Up (Weighted)": (3, "Espalda/Bíceps", "14"),
            "Seated Cable Row": (3, "Espalda", "14"),
            "Seated Cable Row (Wide)": (1, "Espalda", "14"),
            "Bicep Curl (Barbell)": (3, "Bíceps", "14"),
            "Incline Curl": (3, "Bíceps", "14"),
            "Curl biceps": (1, "Bíceps", "14")
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

    ws = conectar_google_sheets()
    tab_entreno, tab_graficas = st.tabs(["🏋️ Entrenar Hoy", "📈 Mi Evolución"])

    with tab_entreno:
        FECHA_INICIO = datetime(2026, 2, 2) 
        semana_actual = ((datetime.now() - FECHA_INICIO).days // 7) + 1
        fase = "MES 1: ADAPTACIÓN" if semana_actual <= 4 else ("MES 2: SOBRECARGA" if semana_actual <= 8 else "MES 3: INTENSIDAD")
        st.markdown(f"<div class='fase-box'><strong>Semana {semana_actual}</strong> | {fase}</div>", unsafe_allow_html=True)

        dia_sel = st.selectbox("Día de entrenamiento", list(config_rutina.keys()))
        
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
            st.markdown(f"<span class='muscle-label'>{info[1]}</span>", unsafe_allow_html=True)
            
            if not df_all.empty:
                df_prev = df_all[(df_all['Ejercicio'] == ex_active) & (df_all['Fecha_Solo'] != hoy_str)]
                if not df_prev.empty:
                    last_date = df_prev['Fecha_Solo'].iloc[-1]
                    with st.expander(f"Ver historial ({last_date})"):
                        for _, r in df_prev[df_prev['Fecha_Solo'] == last_date].iterrows():
                            st.write(f"S{r['Serie']}: {r['Peso']}kg x {r['Repeticiones']}")

            c1, c2, c3 = st.columns([1, 2, 2])
            s_n = c1.number_input("Serie", value=1)
            p_n = c2.number_input("Kg", value=0.0, step=0.5)
            r_n = c3.number_input("Reps", value=10)
            
            if st.button("💾 GUARDAR SERIE"):
                ws.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), dia_sel, ex_active, s_n, r_n, p_n, 8, ""])
                st.toast("¡Serie Guardada!")
                time.sleep(1)
                st.rerun()

    with tab_graficas:
        if not df_all.empty:
            st.subheader("Análisis de Progreso")
            dia_graf = st.selectbox("Filtrar por Rutina", list(config_rutina.keys()), key="graf_dia")
            ejercicios_disponibles = df_all[df_all['Tipo Entrenamiento'] == dia_graf]['Ejercicio'].unique()
            if len(ejercicios_disponibles) > 0:
                ex_graf = st.selectbox("Ejercicio", ejercicios_disponibles, key="graf_ex")
                df_ex = df_all[df_all['Ejercicio'] == ex_graf].copy()
                df_ex['Fecha_DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M")
                df_daily = df_ex.groupby(df_ex['Fecha_DT'].dt.date).agg({'Peso': 'max'}).reset_index()
                fig_peso = px.line(df_daily, x='Fecha_DT', y='Peso', title="Evolución Peso Máximo", markers=True)
                st.plotly_chart(fig_peso, use_container_width=True)



