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
    }
    .history-card {
        background-color: #1c2128; padding: 15px; border-radius: 10px;
        border: 1px solid #30363d; margin-bottom: 10px;
    }
    .metric-container {
        display: flex; justify-content: space-around; background: #0f0f1a;
        padding: 10px; border-radius: 8px; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. AUTENTICACIÓN Y CONEXIÓN ---
def check_password():
    TIEMPO_SESION = timedelta(hours=1, minutes=30)
    
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            st.session_state["login_time"] = datetime.now()
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        tiempo_transcurrido = datetime.now() - st.session_state.get("login_time", datetime.now())
        if tiempo_transcurrido > TIEMPO_SESION:
            st.session_state["password_correct"] = False
            st.error("⌛ Sesión expirada.")
            return False
        return True

    st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
    return False

# --- GESTIÓN DE GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

def get_data(ss):
    # Hoja de Logs
    try:
        ws_logs = ss.worksheet("Logs_Entrenamiento")
    except:
        ws_logs = ss.add_worksheet(title="Logs_Entrenamiento", rows="1000", cols="10")
        ws_logs.append_row(["Fecha", "Tipo Entrenamiento", "Ejercicio", "Serie", "Repeticiones", "Peso", "RPE", "Notas"])
    
    # Hoja de Configuración (NUEVO)
    try:
        ws_config = ss.worksheet("Config_Rutinas")
    except:
        ws_config = ss.add_worksheet(title="Config_Rutinas", rows="100", cols="5")
        ws_config.append_row(["Rutina", "Ejercicio", "Series_Default", "Musculo", "Reps_Objetivo"])
        # Cargar datos por defecto si la hoja es nueva
        default_data = [
            ["Espalda-biceps", "Pull Up (Weighted)", 3, "Espalda", "6-8"],
            ["Espalda-biceps", "Chin Up (Weighted)", 3, "Espalda/Bíceps", "6-8"],
            ["Pecho-triceps-hombro", "Chest Press", 3, "Pecho", "8-10"],
            ["Pierna", "Full Squat", 4, "Pierna", "5-8"]
        ]
        for row in default_data:
            ws_config.append_row(row)

    return ws_logs, ws_config

# --- LÓGICA PRINCIPAL ---
if check_password():
    ss = init_connection()
    ws_logs, ws_config = get_data(ss)

    # Cargar datos en DataFrames
    df_logs = pd.DataFrame(ws_logs.get_all_records())
    df_config = pd.DataFrame(ws_config.get_all_records())

    # Tabs principales
    tab_entreno, tab_graficas, tab_config = st.tabs(["🏋️ Entrenar", "📈 Evolución", "⚙️ Configuración"])

    # ---------------- TAB 1: ENTRENAMIENTO ----------------
    with tab_entreno:
        st.subheader("Panel de Entrenamiento")
        
        # Selector de Rutina basado en la configuración guardada
        if not df_config.empty:
            rutinas_disponibles = df_config['Rutina'].unique().tolist()
            rutina_sel = st.selectbox("Selecciona Rutina", rutinas_disponibles)
            
            # Filtrar ejercicios de esa rutina
            ejercicios_rutina = df_config[df_config['Rutina'] == rutina_sel]
        else:
            st.warning("No hay rutinas configuradas. Ve a la pestaña Configuración.")
            st.stop()

        # Layout columnas
        col_list, col_action = st.columns([1, 2])

        with col_list:
            st.markdown("### Ejercicios")
            # Verificar qué se ha hecho hoy
            hoy_str = datetime.now().strftime("%d/%m/%Y")
            hechos_hoy = []
            if not df_logs.empty:
                df_logs['Fecha_Solo'] = df_logs['Fecha'].apply(lambda x: str(x).split(' ')[0])
                hechos_hoy = df_logs[df_logs['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

            # Botones de ejercicios
            for _, row in ejercicios_rutina.iterrows():
                ex_name = row['Ejercicio']
                is_done = ex_name in hechos_hoy
                btn_label = f"{'✅' if is_done else '⚪'} {ex_name}"
                
                if st.button(btn_label, key=f"btn_{ex_name}", use_container_width=True):
                    st.session_state.ej_activo = ex_name
                    st.session_state.datos_ej_activo = row.to_dict()

        with col_action:
            if "ej_activo" in st.session_state:
                ex_active = st.session_state.ej_activo
                meta_data = st.session_state.datos_ej_activo
                
                st.markdown(f"## 📝 {ex_active}")
                st.caption(f"Músculo: {meta_data['Musculo']} | Objetivo Reps: {meta_data['Reps_Objetivo']}")

                # --- VISUALIZACIÓN DE HISTORIAL MEJORADA ---
                if not df_logs.empty:
                    # Filtrar historial de este ejercicio
                    df_hist = df_logs[df_logs['Ejercicio'] == ex_active].copy()
                    
                    if not df_hist.empty:
                        # Obtener la última fecha de entrenamiento (que no sea hoy)
                        fechas = sorted(df_hist[df_hist['Fecha_Solo'] != hoy_str]['Fecha_Solo'].unique(), reverse=True)
                        
                        if fechas:
                            last_date = fechas[0]
                            df_last = df_hist[df_hist['Fecha_Solo'] == last_date]
                            
                            st.info(f"🔙 **Última sesión ({last_date}):**")
                            # Mostrar tabla limpia
                            st.dataframe(
                                df_last[['Serie', 'Peso', 'Repeticiones', 'RPE']].style.format({'Peso': '{:.1f} kg'}),
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.info("Primera vez haciendo este ejercicio.")
                    else:
                        st.info("Sin historial previo.")

                st.divider()

                # --- INPUT DE NUEVA SERIE ---
                st.markdown("#### Registrar Serie Actual")
                
                # Detectar número de serie automáticamente
                next_serie = 1
                if not df_logs.empty:
                    log_hoy = df_logs[(df_logs['Fecha_Solo'] == hoy_str) & (df_logs['Ejercicio'] == ex_active)]
                    if not log_hoy.empty:
                        next_serie = log_hoy['Serie'].max() + 1
                
                # Columnas de input
                c1, c2, c3, c4 = st.columns(4)
                series_target = c1.number_input("Meta Series", value=int(meta_data['Series_Default']), min_value=1)
                peso_val = c2.number_input("Peso (kg)", value=0.0, step=1.25, format="%.2f")
                reps_val = c3.number_input("Reps", value=int(str(meta_data['Reps_Objetivo']).split('-')[0]) if '-' in str(meta_data['Reps_Objetivo']) else 8)
                rpe_val = c4.select_slider("RPE", options=[6, 7, 8, 9, 10], value=8)
                
                col_btn, col_prog = st.columns([1, 1])
                with col_btn:
                    if st.button("💾 GUARDAR SERIE", type="primary", use_container_width=True):
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
                        st.toast(f"Serie {next_serie} guardada!")
                        time.sleep(1)
                        st.rerun()
                
                with col_prog:
                    st.progress(min(next_serie / series_target, 1.0), text=f"Serie {next_serie-1 if next_serie > 1 else 0} de {series_target} completadas")

            else:
                st.info("👈 Selecciona un ejercicio para empezar")

    # ---------------- TAB 2: GRÁFICAS ----------------
    with tab_graficas:
        if not df_logs.empty:
            st.subheader("📈 Análisis de Progreso")
            
            all_ejercicios = sorted(df_logs['Ejercicio'].unique())
            ex_graf = st.selectbox("Analizar Ejercicio", all_ejercicios)
            
            df_ex = df_logs[df_logs['Ejercicio'] == ex_graf].copy()
            df_ex['Fecha_DT'] = pd.to_datetime(df_ex['Fecha'], format="%d/%m/%Y %H:%M")
            
            # Agrupar por día (máximo peso movido ese día)
            df_daily = df_ex.groupby(df_ex['Fecha_DT'].dt.date).agg({'Peso': 'max', 'Repeticiones': 'max'}).reset_index()
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                fig_peso = px.line(df_daily, x='Fecha_DT', y='Peso', title="Evolución Carga Máxima (Kg)", markers=True, line_shape='spline')
                fig_peso.update_layout(xaxis_title="Fecha", yaxis_title="Kg")
                st.plotly_chart(fig_peso, use_container_width=True)
                
            with col_g2:
                # Volumen total (Series x Reps x Peso)
                df_ex['Volumen'] = df_ex['Peso'] * df_ex['Repeticiones']
                df_vol = df_ex.groupby(df_ex['Fecha_DT'].dt.date)['Volumen'].sum().reset_index()
                fig_vol = px.bar(df_vol, x='Fecha_DT', y='Volumen', title="Volumen Total de Entrenamiento")
                st.plotly_chart(fig_vol, use_container_width=True)
                
            st.dataframe(df_daily.sort_values('Fecha_DT', ascending=False), use_container_width=True)

    # ---------------- TAB 3: CONFIGURACIÓN (AÑADIR EJERCICIOS) ----------------
    with tab_config:
        st.header("⚙️ Gestión de Rutinas")
        st.info("Aquí puedes añadir nuevos ejercicios que se guardarán permanentemente en Google Sheets.")
        
        with st.form("add_exercise_form"):
            col_a, col_b = st.columns(2)
            new_rutina = col_a.text_input("Nombre de la Rutina (ej: Pierna, Empuje)", placeholder="Espalda-biceps")
            new_ejercicio = col_b.text_input("Nombre del Ejercicio", placeholder="Sentadilla Hack")
            
            col_c, col_d, col_e = st.columns(3)
            new_series = col_c.number_input("Series Objetivo (Default)", min_value=1, value=3)
            new_reps = col_d.text_input("Rango Reps", value="8-12")
            new_musculo = col_e.text_input("Grupo Muscular", placeholder="Cuádriceps")
            
            submitted = st.form_submit_button("➕ Añadir Ejercicio")
            
            if submitted:
                if new_rutina and new_ejercicio:
                    ws_config.append_row([new_rutina, new_ejercicio, new_series, new_musculo, new_reps])
                    st.success(f"Ejercicio '{new_ejercicio}' añadido a '{new_rutina}'")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Faltan campos por rellenar.")
        
        st.subheader("Ejercicios Configurados Actualmente")
        st.dataframe(df_config, use_container_width=True)
