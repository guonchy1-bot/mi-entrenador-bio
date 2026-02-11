import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.express as px
import streamlit as st

def check_password():
    """Devuelve True si el usuario introdujo la contraseña correcta."""

    def password_entered():
        """Revisa si la contraseña coincide."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Borra la contraseña del state por seguridad
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primer inicio, muestra el campo de entrada
        st.text_input(
            "Introduce la contraseña para acceder", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta, vuelve a mostrar el campo
        st.text_input(
            "Contraseña incorrecta, intenta de nuevo", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Contraseña errónea")
        return False
    else:
        # Contraseña correcta
        return True

if check_password():
    # --- AQUÍ VA TODO EL CONTENIDO DE TU APP ---
    st.title("🚀 Mi App Protegida")
    st.write("Si ves esto, es porque la contraseña es correcta.")

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
    /* Importación de fuente premium */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* Configuración global del contenedor principal */
    .main {
        background-color: #0E1117;
        font-family: 'Outfit', sans-serif;
    }

    /* Estilo de la caja de Fase/Semana (Efecto Gradiente Nocturno) */
    .fase-box {
        background: linear-gradient(135deg, #1e1e2f 0%, #0f0f1a 100%);
        color: #ffffff;
        padding: 24px;
        border-radius: 20px;
        border: 1px solid #3d3d5c;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        text-align: center;
        margin-bottom: 30px;
    }

    /* Botones de Ejercicios (Minimalismo Extremo) */
    .stButton > button {
        background-color: #161b22;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px 20px;
        transition: all 0.2s ease-in-out;
        text-align: left;
        width: 100%;
        font-size: 16px;
        font-weight: 500;
    }

    .stButton > button:hover {
        border-color: #58a6ff;
        background-color: #1c2128;
        color: #58a6ff;
        transform: translateX(5px);
    }

    /* Tabs (Pestañas) personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #161b22;
        border-radius: 10px;
        color: #8b949e;
        border: 1px solid #30363d;
        padding: 0 25px;
        transition: 0.3s;
    }

    .stTabs [aria-selected="true"] {
        background-color: #238636 !important; /* Verde deportivo */
        color: white !important;
        border: none !important;
    }

    /* Inputs y Number Inputs */
    input {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }

    /* Etiquetas de Músculos (Estilo Badge) */
    .muscle-label {
        background-color: rgba(88, 166, 255, 0.1);
        color: #58a6ff;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid rgba(88, 166, 255, 0.3);
    }

    /* Métrica de Descanso (Timer) */
    [data-testid="stMetricValue"] {
        color: #ff7b72; /* Color coral para urgencia */
        font-family: 'Monospace';
        font-weight: 700;
    }

    /* Divider estilizado */
    hr {
        border-top: 1px solid #30363d;
        margin: 2em 0;
    }

    /* Esconder el menú de Streamlit para limpieza total */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

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





