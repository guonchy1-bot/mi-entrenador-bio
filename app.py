import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    .main { background-color: #0E1117; font-family: 'Outfit', sans-serif; }
    .stButton > button {
        border-radius: 8px; font-weight: 600; width: 100%;
        text-align: left; padding-left: 15px;
        border: 1px solid #30363d;
    }
    .stButton > button:hover {
        border-color: #58a6ff; color: #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. GESTIÓN DE GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    # Corrección de saltos de línea en la clave privada
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

def get_data(ss):
    # A. Hoja de Logs (Historial)
    try:
        ws_logs = ss.worksheet("Logs_Entrenamiento")
    except:
        ws_logs = ss.add_worksheet(title="Logs_Entrenamiento", rows="2000", cols="10")
        ws_logs.append_row(["Fecha", "Tipo Entrenamiento", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"])
    
    # B. Hoja de Configuración (Rutinas)
    try:
        ws_config = ss.worksheet("Config_Rutinas")
    except:
        ws_config = ss.add_worksheet(title="Config_Rutinas", rows="100", cols="5")
        ws_config.append_row(["Rutina", "Ejercicio", "Series_Default", "Musculo", "Reps_Objetivo"])

    # --- MIGRACIÓN: CARGA TUS DATOS ORIGINALES SI LA HOJA ESTÁ VACÍA ---
    if len(ws_config.get_all_values()) <= 1:
        
        # TU CONFIGURACIÓN EXACTA
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
        
        # Subir a Google Sheets
        for rutina, ejercicios in config_rutina_original.items():
            for nombre_ej, datos in ejercicios.items():
                # [Rutina, Ejercicio, Series, Musculo, Reps]
                ws_config.append_row([rutina, nombre_ej, datos[0], datos[1], datos[2]])
                time.sleep(0.1) # Pausa pequeña para seguridad

    return ws_logs, ws_config

# --- LÓGICA PRINCIPAL (YA SIN CONTRASEÑA) ---
ss = init_connection()
ws_logs, ws_config = get_data(ss)

df_logs = pd.DataFrame(ws_logs.get_all_records())
df_config = pd.DataFrame(ws_config.get_all_records())

tab_entreno, tab_graficas, tab_config = st.tabs(["🏋️ Entrenar", "📈 Evolución", "⚙️ Configuración"])

# ---------------- TAB 1: ENTRENAMIENTO ----------------
with tab_entreno:
    st.subheader("Panel de Entrenamiento")
    
    if not df_config.empty:
        rutinas_disponibles = df_config['Rutina'].unique().tolist()
        rutina_sel = st.selectbox("Selecciona Rutina", rutinas_disponibles)
        ejercicios_rutina = df_config[df_config['Rutina'] == rutina_sel]
    else:
        st.warning("Cargando tu configuración... Por favor recarga la página.")
        st.stop()

    col_list, col_action = st.columns([1, 2])

    # --- COLUMNA IZQUIERDA: LISTA DE EJERCICIOS ---
    with col_list:
        st.markdown("### Ejercicios")
        hoy_str = datetime.now().strftime("%d/%m/%Y")
        
        # Chequear hechos hoy
        hechos_hoy = []
        if not df_logs.empty and 'Fecha' in df_logs.columns:
            df_logs['Fecha_Solo'] = df_logs['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
            hechos_hoy = df_logs[df_logs['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

        # Renderizar botones
        for _, row in ejercicios_rutina.iterrows():
            ex_name = row['Ejercicio']
            is_done = ex_name in hechos_hoy
            btn_str = f"✅ {ex_name}" if is_done else f"⚪ {ex_name}"
            
            if st.button(btn_str, key=f"btn_{ex_name}", use_container_width=True):
                st.session_state.ej_activo = ex_name
                st.session_state.datos_ej_activo = row.to_dict()

    # --- COLUMNA DERECHA: ÁREA DE TRABAJO ---
    with col_action:
        if "ej_activo" in st.session_state:
            ex_active = st.session_state.ej_activo
            meta_data = st.session_state.datos_ej_activo
            
            st.markdown(f"## 📝 {ex_active}")
            
            c_inf1, c_inf2 = st.columns(2)
            c_inf1.info(f"💪 **{meta_data['Musculo']}**")
            c_inf2.info(f"🎯 Meta: **{meta_data['Reps_Objetivo']} reps**")

            # --- HISTORIAL VISUAL ---
            if not df_logs.empty:
                df_hist = df_logs[df_logs['Ejercicio'] == ex_active].copy()
                
                if not df_hist.empty:
                    # Filtrar para no mostrar lo de hoy como "historial"
                    fechas_previas = df_hist[df_hist['Fecha_Solo'] != hoy_str]['Fecha_Solo'].unique()
                    
                    if len(fechas_previas) > 0:
                        # Ordenar fechas correctamente
                        df_hist['DT'] = pd.to_datetime(df_hist['Fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
                        # Obtener la fecha más reciente que NO sea hoy
                        last_valid_date_dt = df_hist[df_hist['Fecha_Solo'] != hoy_str].sort_values('DT', ascending=False)['DT'].iloc[0]
                        last_valid_date_str = last_valid_date_dt.strftime("%d/%m/%Y") # Formato visual limpio
                        
                        df_last = df_hist[df_hist['Fecha_Solo'] == last_valid_date_str]
                        
                        st.markdown(f"**🗓️ Última sesión ({last_valid_date_str}):**")
                        st.dataframe(
                            df_last[['Serie', 'Peso', 'Repeticiones', 'RPE']].style.format({'Peso': '{:.1f} kg'}),
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.caption("No hay sesiones anteriores guardadas.")
                else:
                    st.caption("Primer registro para este ejercicio.")

            st.divider()

            # --- INPUT Y GUARDADO ---
            st.markdown("#### Registrar Serie")
            
            # Calcular número de serie automático
            next_serie = 1
            if not df_logs.empty:
                log_hoy = df_logs[(df_logs['Fecha_Solo'] == hoy_str) & (df_logs['Ejercicio'] == ex_active)]
                if not log_hoy.empty:
                    try:
                        next_serie = int(log_hoy['Serie'].max()) + 1
                    except:
                        next_serie = 1
            
            with st.form("serie_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                peso_val = c1.number_input("Kilos", min_value=0.0, step=1.25, format="%.2f", key="in_peso")
                reps_val = c2.number_input("Reps", min_value=1, value=int(str(meta_data['Reps_Objetivo']).split('-')[0]) if '-' in str(meta_data['Reps_Objetivo']) and str(meta_data['Reps_Objetivo']).split('-')[0].isdigit() else 8, key="in_reps")
                rpe_val = c3.slider("RPE", 5, 10, 8, key="in_rpe")
                
                # EDITAR SERIES OBJETIVO (SOLO PARA ESTA SESIÓN)
                series_target = st.number_input("Meta de Series Hoy", value=int(meta_data['Series_Default']), min_value=1)

                if st.form_submit_button("💾 GUARDAR SERIE", type="primary", use_container_width=True):
                    new_row = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        rutina_sel,
                        ex_active,
                        next_serie,
                        reps_val,
                        peso_val,
                        rpe_val,
                        ""
                    ]
                    ws_logs.append_row(new_row)
                    st.toast(f"✅ Serie {next_serie} registrada")
                    time.sleep(1)
                    st.rerun()

            # Barra de progreso
            progreso = min((next_serie - 1) / series_target, 1.0)
            st.progress(progreso, text=f"Completadas: {next_serie-1} / {series_target}")

        else:
            st.info("👈 Selecciona un ejercicio para ver tus datos.")

# ---------------- TAB 2: GRÁFICAS ----------------
with tab_graficas:
    if not df_logs.empty:
        st.subheader("📈 Progreso de Cargas")
        
        all_ejercicios = sorted(df_logs['Ejercicio'].unique())
        if all_ejercicios:
            ex_graf = st.selectbox("Ejercicio a analizar", all_ejercicios)
            
            df_ex = df_logs[df_logs['Ejercicio'] == ex_graf].copy()
            df_ex['Fecha_DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
            df_ex = df_ex.dropna(subset=['Fecha_DT'])
            
            # Agrupar por día (Max Peso)
            df_daily = df_ex.groupby(df_ex['Fecha_DT'].dt.date).agg({'Peso': 'max'}).reset_index()
            
            fig = px.line(df_daily, x='Fecha_DT', y='Peso', markers=True, title=f"Evolución Peso Máximo: {ex_graf}")
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Kg")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aun no hay datos registrados.")

# ---------------- TAB 3: CONFIGURACIÓN ----------------
with tab_config:
    st.header("⚙️ Añadir Nuevos Ejercicios")
    
    with st.form("add_exercise_form"):
        col_a, col_b = st.columns(2)
        # Autocompletar rutinas existentes
        rutinas_existentes = df_config['Rutina'].unique().tolist() if not df_config.empty else []
        
        new_rutina_input = col_a.text_input("Nombre Rutina (Escribe nueva o existente)", placeholder="Ej: Pierna")
        if rutinas_existentes:
            col_a.caption(f"Existentes: {', '.join(rutinas_existentes)}")
            
        new_ejercicio = col_b.text_input("Nombre del Ejercicio", placeholder="Ej: Hip Thrust")
        
        col_c, col_d, col_e = st.columns(3)
        new_series = col_c.number_input("Series Default", 1, 10, 3)
        new_reps = col_d.text_input("Rango Reps", "8-12")
        new_musculo = col_e.text_input("Músculo Principal", "Glúteo")
        
        if st.form_submit_button("➕ Añadir Ejercicio"):
            if new_rutina_input and new_ejercicio:
                ws_config.append_row([new_rutina_input, new_ejercicio, new_series, new_musculo, new_reps])
                st.success("Ejercicio añadido. Ve a 'Entrenar' para verlo.")
                time.sleep(1.5)
                st.rerun()

    st.subheader("Base de Datos de Ejercicios")
    st.dataframe(df_config, use_container_width=True)
