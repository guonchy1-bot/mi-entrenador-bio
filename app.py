import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

# --- DISEÑO & CSS (ESTILO DARK/NEON) ---
st.markdown("""
    <style>
    /* Importar fuente moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Fondo y contenedores */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Tarjetas de Métricas */
    .metric-container {
        background-color: #1a1c24;
        border: 1px solid #2d333b;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-value {
        font-size: 24px;
        font-weight: 800;
        color: #58a6ff;
    }
    .metric-label {
        font-size: 12px;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 5px;
    }

    /* Botones de Ejercicios */
    .stButton > button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        transition: all 0.2s;
        text-align: left;
        display: flex;
        align-items: center;
        width: 100%;
    }
    .stButton > button:hover {
        border-color: #58a6ff;
        color: #58a6ff;
        transform: translateX(3px);
    }
    .stButton > button:active {
        background-color: #58a6ff;
        color: white;
    }

    /* Tablas */
    div[data-testid="stDataFrame"] {
        background-color: #161b22;
        padding: 10px;
        border-radius: 10px;
    }

    /* Encabezados */
    h1, h2, h3 {
        color: #ffffff;
    }
    .highlight {
        color: #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MAPA DE ICONOS ---
MUSCLE_ICONS = {
    "Espalda": "🦇", "Bíceps": "💪", "Pecho": "🦍", "Tríceps": "🔨",
    "Hombro": "🥥", "Pierna": "🍗", "Cuádriceps": "🦵", "Femoral": "🥓",
    "Gemelos": "💎", "Glúteo": "🍑", "Abdomen": "🍫"
}

def get_icon(musculo):
    for key, icon in MUSCLE_ICONS.items():
        if key.lower() in str(musculo).lower():
            return icon
    return "🏋️"

# --- CONEXIÓN ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

def get_data(ss):
    try:
        ws_logs = ss.worksheet("Logs_Entrenamiento")
    except:
        ws_logs = ss.add_worksheet(title="Logs_Entrenamiento", rows="2000", cols="10")
        ws_logs.append_row(["Fecha", "Tipo Entrenamiento", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"])
    
    try:
        ws_config = ss.worksheet("Config_Rutinas")
    except:
        ws_config = ss.add_worksheet(title="Config_Rutinas", rows="100", cols="5")
        ws_config.append_row(["Rutina", "Ejercicio", "Series_Default", "Musculo", "Reps_Objetivo"])

    # --- MIGRACIÓN AUTOMÁTICA (Mantiene tu lógica original) ---
    if len(ws_config.get_all_values()) <= 1:
        config_rutina_original = {
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
        for rutina, ejercicios in config_rutina_original.items():
            for nombre_ej, datos in ejercicios.items():
                ws_config.append_row([rutina, nombre_ej, datos[0], datos[1], datos[2]])
                time.sleep(0.1)

    return ws_logs, ws_config

# --- INICIO ---
ss = init_connection()
ws_logs, ws_config = get_data(ss)

# Cargar Dataframes
df_logs = pd.DataFrame(ws_logs.get_all_records())
df_config = pd.DataFrame(ws_config.get_all_records())

# Título Bonito
st.markdown("### 🧬 Bio-Hypertrophy <span class='highlight'>Pro</span>", unsafe_allow_html=True)
tab_entreno, tab_graficas, tab_config = st.tabs(["🔥 ENTRENAR", "📈 ESTADÍSTICAS", "⚙️ AJUSTES"])

# --- TAB 1: ENTRENAMIENTO ---
with tab_entreno:
    if not df_config.empty:
        # Selector de rutina limpio
        rutinas = df_config['Rutina'].unique().tolist()
        rutina_sel = st.selectbox("Selecciona tu sesión de hoy", rutinas)
        ejercicios_rutina = df_config[df_config['Rutina'] == rutina_sel]
    else:
        st.warning("Cargando datos...")
        st.stop()

    col_izq, col_der = st.columns([1, 1.8], gap="medium")

    # --- LISTA EJERCICIOS (IZQUIERDA) ---
    with col_izq:
        st.markdown("##### 📋 Menú de Ejercicios")
        hoy_str = datetime.now().strftime("%d/%m/%Y")
        
        hechos_hoy = []
        if not df_logs.empty and 'Fecha' in df_logs.columns:
            df_logs['Fecha_Solo'] = df_logs['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
            hechos_hoy = df_logs[df_logs['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

        # Barra de progreso general del día
        total_ej = len(ejercicios_rutina)
        completados = len([e for e in ejercicios_rutina['Ejercicio'] if e in hechos_hoy])
        progreso_dia = completados / total_ej if total_ej > 0 else 0
        st.progress(progreso_dia)
        st.caption(f"{completados}/{total_ej} ejercicios completados")

        for _, row in ejercicios_rutina.iterrows():
            ex_name = row['Ejercicio']
            icon = get_icon(row['Musculo'])
            
            # Estilo condicional
            if ex_name in hechos_hoy:
                label = f"✅ {ex_name}"
            elif "ej_activo" in st.session_state and st.session_state.ej_activo == ex_name:
                label = f"🔵 {ex_name}" # Seleccionado
            else:
                label = f"{icon} {ex_name}"
            
            if st.button(label, key=f"btn_{ex_name}"):
                st.session_state.ej_activo = ex_name
                st.session_state.datos_ej_activo = row.to_dict()

    # --- ÁREA DE TRABAJO (DERECHA) ---
    with col_der:
        if "ej_activo" in st.session_state:
            ex_active = st.session_state.ej_activo
            meta = st.session_state.datos_ej_activo
            
            # 1. ENCABEZADO Y MÉTRICAS CLAVE
            st.markdown(f"#### {ex_active}")
            
            # Calcular Stats Rápidas
            record_peso = 0
            last_peso = 0
            last_reps = 0
            
            if not df_logs.empty:
                df_ex = df_logs[df_logs['Ejercicio'] == ex_active]
                if not df_ex.empty:
                    record_peso = df_ex['Peso'].max()
                    # Última sesión (no hoy)
                    df_prev = df_ex[df_ex['Fecha_Solo'] != hoy_str]
                    if not df_prev.empty:
                        # Convertir fechas para ordenar
                        df_prev = df_prev.copy() # Evitar warning
                        df_prev['DT'] = pd.to_datetime(df_prev['Fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
                        last_idx = df_prev['DT'].idxmax()
                        last_peso = df_prev.loc[last_idx, 'Peso']
                        last_reps = df_prev.loc[last_idx, 'Repeticiones']

            # Tarjetas de Métricas (HTML/CSS Personalizado)
            m1, m2, m3 = st.columns(3)
            m1.markdown(f"<div class='metric-container'><div class='metric-value'>{meta['Reps_Objetivo']}</div><div class='metric-label'>Meta Reps</div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-container'><div class='metric-value'>{last_peso} <span style='font-size:12px'>kg</span></div><div class='metric-label'>Último Peso</div></div>", unsafe_allow_html=True)
            m3.markdown(f"<div class='metric-container'><div class='metric-value' style='color:#7ee787'>{record_peso} <span style='font-size:12px'>kg</span></div><div class='metric-label'>Récord (PR)</div></div>", unsafe_allow_html=True)

            st.divider()

            # 2. HISTORIAL RECIENTE (Tabla limpia)
            if not df_logs.empty:
                df_hist = df_logs[(df_logs['Ejercicio'] == ex_active) & (df_logs['Fecha_Solo'] != hoy_str)].copy()
                if not df_hist.empty:
                    df_hist['DT'] = pd.to_datetime(df_hist['Fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
                    last_date = df_hist.sort_values('DT', ascending=False).iloc[0]['Fecha_Solo']
                    df_last_session = df_hist[df_hist['Fecha_Solo'] == last_date]
                    
                    with st.expander(f"🕰️ Ver sesión anterior ({last_date})", expanded=False):
                        st.dataframe(
                            df_last_session[['Serie', 'Peso', 'Repeticiones', 'RPE']].style.background_gradient(cmap='Blues', subset=['Peso']),
                            hide_index=True, use_container_width=True
                        )

            # 3. INPUT DE DATOS (FORMULARIO)
            st.markdown("###### 📝 Registrar Nueva Serie")
            
            # Auto-calcular serie
            next_serie = 1
            if not df_logs.empty:
                log_hoy = df_logs[(df_logs['Fecha_Solo'] == hoy_str) & (df_logs['Ejercicio'] == ex_active)]
                if not log_hoy.empty:
                    try: next_serie = int(log_hoy['Serie'].max()) + 1
                    except: pass
            
            with st.form("log_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                # Valores por defecto inteligentes (basados en historial)
                def_peso = float(last_peso) if last_peso > 0 else 0.0
                def_reps = int(last_reps) if last_reps > 0 else 10
                
                peso_in = c1.number_input("Peso (kg)", value=def_peso, step=1.25, format="%.2f")
                reps_in = c2.number_input("Reps", value=def_reps, step=1)
                rpe_in = c3.select_slider("RPE", options=[6, 7, 8, 9, 10], value=8)
                
                # Notas opcionales y Meta de Series editable
                c4, c5 = st.columns([2, 1])
                notas_in = c4.text_input("Notas (opcional)", placeholder="Ej: Sentí molestias...")
                series_target = c5.number_input("Meta Series", value=int(meta['Series_Default']), min_value=1)

                btn_save = st.form_submit_button("💾 GUARDAR SERIE", type="primary", use_container_width=True)

                if btn_save:
                    new_row = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        rutina_sel, ex_active, next_serie, reps_in, peso_in, rpe_in, notas_in
                    ]
                    ws_logs.append_row(new_row)
                    
                    # Feedback visual (Celebración si es PR)
                    if peso_in > record_peso and record_peso > 0:
                        st.balloons()
                        st.toast(f"🎉 ¡NUEVO PR! {peso_in}kg")
                    else:
                        st.toast(f"✅ Serie {next_serie} guardada")
                    
                    time.sleep(1)
                    st.rerun()
            
            # Barra de progreso de la sesión actual del ejercicio
            prog = min((next_serie - 1) / series_target, 1.0)
            st.progress(prog, text=f"Serie {next_serie-1} de {series_target}")

        else:
            # Estado vacio bonito
            st.info("👈 Selecciona un ejercicio del menú para comenzar a registrar.")
            st.markdown("""
                <div style='text-align: center; color: #30363d; margin-top: 50px;'>
                    <h1>🏋️</h1>
                    <p>Selecciona un ejercicio a la izquierda</p>
                </div>
            """, unsafe_allow_html=True)

# --- TAB 2: ESTADÍSTICAS ---
with tab_graficas:
    st.subheader("📈 Evolución de Cargas")
    
    if not df_logs.empty:
        all_exs = sorted(df_logs['Ejercicio'].unique())
        ex_graf = st.selectbox("Analizar Ejercicio", all_exs)
        
        df_ex = df_logs[df_logs['Ejercicio'] == ex_graf].copy()
        df_ex['DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
        df_ex = df_ex.dropna(subset=['DT'])
        
        # Agrupar: Máximo peso por día
        df_daily = df_ex.groupby(df_ex['DT'].dt.date).agg({'Peso': 'max', 'Repeticiones': 'mean'}).reset_index()
        
        # Gráfica Plotly con tema oscuro/neon
        fig = px.line(df_daily, x='DT', y='Peso', markers=True, 
                      title=f"Progreso en {ex_graf}", template="plotly_dark")
        
        # Personalizar colores
        fig.update_traces(line_color='#58a6ff', marker=dict(size=8, color='#7ee787'))
        fig.update_layout(
            xaxis_title=None,
            yaxis_title="Peso Máximo (kg)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de resumen
        st.caption("Historial Detallado")
        st.dataframe(df_daily.sort_values('DT', ascending=False), use_container_width=True)
    else:
        st.info("No hay datos suficientes para generar gráficas.")

# --- TAB 3: CONFIGURACIÓN ---
with tab_config:
    st.markdown("### ⚙️ Añadir Ejercicios")
    
    with st.form("add_ex"):
        c1, c2 = st.columns(2)
        existentes = df_config['Rutina'].unique().tolist() if not df_config.empty else []
        
        rut_in = c1.text_input("Rutina (Nueva o Existente)", placeholder="Ej: Empuje")
        if existentes: c1.caption(f"Existentes: {', '.join(existentes)}")
        
        nom_in = c2.text_input("Nombre Ejercicio", placeholder="Ej: Face Pull")
        
        c3, c4, c5 = st.columns(3)
        ser_in = c3.number_input("Series Default", 1, 10, 3)
        rep_in = c4.text_input("Rango Reps", "10-15")
        mus_in = c5.text_input("Músculo", placeholder="Hombro Post.")
        
        if st.form_submit_button("➕ Añadir a la Base de Datos"):
            if rut_in and nom_in:
                ws_config.append_row([rut_in, nom_in, ser_in, mus_in, rep_in])
                st.success("Ejercicio añadido exitosamente.")
                time.sleep(1.5)
                st.rerun()
    
    st.divider()
    st.caption("Base de datos actual:")
    st.dataframe(df_config, use_container_width=True)
