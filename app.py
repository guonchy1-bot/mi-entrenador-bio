import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import time
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bio-Hypertrophy Pro", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

# --- DISEÑO & CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0e1117; }
    .metric-container {
        background-color: #1a1c24;
        border: 1px solid #2d333b;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-value { font-size: 24px; font-weight: 800; color: #58a6ff; }
    .metric-label { font-size: 12px; color: #8b949e; text-transform: uppercase; margin-top: 5px; }
    .last-set-box {
        background-color: #21262d;
        border-left: 5px solid #7ee787;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN Y EXTRACCIÓN DE DATOS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Entrenamientos_RayPeat")

def get_data(ss):
    ws_logs = ss.worksheet("Logs_Entrenamiento")
    ws_config = ss.worksheet("Config_Rutinas")
    
    # Intentar cargar la hoja de Datos Personales
    try:
        ws_perfil = ss.worksheet("Datos_Personales")
        df_perfil = pd.DataFrame(ws_perfil.get_all_records())
    except gspread.exceptions.WorksheetNotFound:
        ws_perfil = None
        df_perfil = pd.DataFrame()
    
    data = ws_logs.get_all_values()
    
    if len(data) > 1:
        headers = data[0]
        df = pd.DataFrame(data[1:], columns=headers)
        
        # Limpiamos Peso y Repeticiones manualmente de forma segura
        df['Peso'] = df['Peso'].astype(str).str.replace(',', '.')
        df['Peso'] = pd.to_numeric(df['Peso'], errors='coerce').fillna(0.0)
        
        df['Repeticiones'] = df['Repeticiones'].astype(str).str.replace(',', '.')
        df['Repeticiones'] = pd.to_numeric(df['Repeticiones'], errors='coerce').fillna(0)
    else:
        # Si la hoja está vacía
        df = pd.DataFrame(columns=data[0] if data else [])
        
    return ws_logs, ws_config, ws_perfil, df, df_perfil

# --- FUNCIÓN DE CONSEJO INTELIGENTE (COACH) ---
def obtener_consejo_coach(df_ex):
    if df_ex.empty:
        return "✨ **¡Primer registro!** Establece una base sólida hoy para poder superarte la próxima semana."
    
    df_temp = df_ex.copy()
    df_temp['Fecha_Dia'] = df_temp['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
    hoy_str = datetime.now().strftime("%d/%m/%Y")
    
    sesiones_pasadas = df_temp[df_temp['Fecha_Dia'] != hoy_str]
    
    if sesiones_pasadas.empty:
        return "🎯 **Segunda serie del día:** Intenta mantener la intensidad de la primera."

    ultima_fecha = sesiones_pasadas['Fecha_Dia'].iloc[-1]
    datos_last = sesiones_pasadas[sesiones_pasadas['Fecha_Dia'] == ultima_fecha]
    
    mejor_peso = datos_last['Peso'].max()
    mejor_reps = datos_last[datos_last['Peso'] == mejor_peso]['Repeticiones'].max()

    if mejor_peso == 0:
        return f"💪 La última vez hiciste sin lastre extra. **Reto:** Intenta hacer {int(mejor_reps + 1)} repeticiones hoy."
    
    consejo = f"💡 **Récord anterior ({ultima_fecha}):** {mejor_peso}kg (de lastre) x {int(mejor_reps)} reps. "
    consejo += f"\n\n**Tu objetivo hoy:** ¡Haz {int(mejor_reps + 1)} reps con {mejor_peso}kg O mantén las {int(mejor_reps)} reps pero sube a {mejor_peso + 1.25}kg!"
    
    return consejo

# --- INICIO DE LA APLICACIÓN ---
ss = init_connection()
ws_logs, ws_config, ws_perfil, df_logs, df_perfil = get_data(ss)

# Para la config, get_all_records() es seguro
df_config = pd.DataFrame(ws_config.get_all_records())

st.markdown("### 🧬 Bio-Hypertrophy <span class='highlight'>Pro</span>", unsafe_allow_html=True)
tab_entreno, tab_graficas, tab_config = st.tabs(["🔥 ENTRENAR", "📈 ESTADÍSTICAS", "⚙️ AJUSTES"])

# ==========================================
# PESTAÑA 1: ENTRENAMIENTO
# ==========================================
with tab_entreno:
    if not df_config.empty:
        rutinas = df_config['Rutina'].unique().tolist()
        rutina_sel = st.selectbox("Selecciona tu sesión", rutinas)
        ejercicios_rutina = df_config[df_config['Rutina'] == rutina_sel]
    
    col_izq, col_der = st.columns([1, 1.8], gap="medium")

    with col_izq:
        st.markdown("##### 📋 Ejercicios")
        hoy_str = datetime.now().strftime("%d/%m/%Y")
        hechos_hoy = []
        if not df_logs.empty:
            df_logs['Fecha_Solo'] = df_logs['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
            hechos_hoy = df_logs[df_logs['Fecha_Solo'] == hoy_str]['Ejercicio'].unique()

        for _, row in ejercicios_rutina.iterrows():
            ex_name = row['Ejercicio']
            label = f"{'✅' if ex_name in hechos_hoy else '⚪'} {ex_name}"
            if st.button(label, key=f"btn_{ex_name}", use_container_width=True):
                st.session_state.ej_activo = ex_name
                st.session_state.datos_ej_activo = row.to_dict()

    with col_der:
        if "ej_activo" in st.session_state:
            ex_active = st.session_state.ej_activo
            meta = st.session_state.datos_ej_activo
            
            st.markdown(f"#### {ex_active}")
            
            # --- LÓGICA DE SERIES ---
            log_hoy = df_logs[(df_logs['Fecha_Solo'] == hoy_str) & (df_logs['Ejercicio'] == ex_active)] if not df_logs.empty else pd.DataFrame()
            n_hechas = len(log_hoy)
            next_serie = n_hechas + 1  
            
            # --- MOSTRAR ÚLTIMA SERIE REALIZADA HOY ---
            if not log_hoy.empty:
                ultima_fila = log_hoy.iloc[-1]
                st.markdown(f"""
                <div class="last-set-box">
                    <strong>Anterior Serie (Hecha ahora):</strong> {ultima_fila['Peso']}kg (Lastre/Peso Externo) x {ultima_fila['Repeticiones']} reps (RPE {ultima_fila['RPE']})
                </div>
                """, unsafe_allow_html=True)

            # --- STATS HISTÓRICOS ---
            df_ex = df_logs[df_logs['Ejercicio'] == ex_active] if not df_logs.empty else pd.DataFrame()
            record_peso = df_ex['Peso'].max() if not df_ex.empty else 0
            
            m1, m2 = st.columns(2)
            m1.markdown(f"<div class='metric-container'><div class='metric-value'>{record_peso} <span style='font-size:12px'>kg</span></div><div class='metric-label'>Récord Lastre/Peso Externo</div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-container'><div class='metric-value' style='color:#7ee787'>{next_serie} <span style='font-size:12px'>/ {meta['Series_Default']}</span></div><div class='metric-label'>Serie Actual</div></div>", unsafe_allow_html=True)

            st.divider()
            
            # Mostrar el consejo del Coach
            consejo = obtener_consejo_coach(df_ex)
            st.info(consejo)

            # --- INPUT DE DATOS ---
            series_target = int(meta['Series_Default'])
            prog = min((next_serie - 1) / series_target, 1.0)
            st.progress(prog)
            st.caption(f"Estás por registrar la **Serie {next_serie}** de {series_target}")

            with st.form("log_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                
                # Sugerir el peso de la serie anterior
                sug_peso = float(log_hoy.iloc[-1]['Peso']) if not log_hoy.empty else 0.0
                if sug_peso == 0 and not df_ex.empty:
                    sesiones_previas = df_ex[df_ex['Fecha_Solo'] != hoy_str]
                    if not sesiones_previas.empty:
                        sug_peso = float(sesiones_previas.iloc[-1]['Peso'])

                peso_in = c1.number_input("Lastre/Peso (kg)", value=sug_peso, step=1.25, format="%.2f")
                reps_in = c2.number_input("Reps", value=10, step=1)
                rpe_in = c3.select_slider("RPE", options=[6, 7, 8, 9, 10], value=8)
                notas_in = st.text_input("Notas")

                if st.form_submit_button("💾 GUARDAR SERIE", type="primary", use_container_width=True):
                    new_row = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        rutina_sel, 
                        ex_active, 
                        next_serie, 
                        reps_in, 
                        peso_in, 
                        rpe_in, 
                        notas_in
                    ]
                    ws_logs.append_row(new_row, value_input_option='USER_ENTERED')
                    
                    st.toast(f"✅ Serie {next_serie} guardada")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("👈 Selecciona un ejercicio en el panel izquierdo para empezar.")

# ==========================================
# PESTAÑA 2: ESTADÍSTICAS (PREMIUM UI)
# ==========================================
with tab_graficas:
    st.markdown("### 📈 Análisis de Progreso")
    
    if df_logs.empty:
        st.info("Aún no hay datos suficientes para mostrar gráficas.")
    else:
        ejercicios_disp = sorted(df_logs['Ejercicio'].unique().tolist())
        col_sel, _ = st.columns([2,1])
        with col_sel:
             ej_seleccionado = st.selectbox("🔍 Analizar Ejercicio:", ejercicios_disp)
        
        df_graf = df_logs[df_logs['Ejercicio'] == ej_seleccionado].copy()
        
        if not df_graf.empty:
            # --- PROCESAMIENTO DE DATOS ---
            if 'Fecha_Solo' not in df_graf.columns:
                df_graf['Fecha_Solo'] = df_graf['Fecha'].astype(str).apply(lambda x: x.split(' ')[0])
                
            df_graf['Fecha_DT'] = pd.to_datetime(df_graf['Fecha_Solo'], format="%d/%m/%Y")
            df_graf = df_graf.sort_values('Fecha_DT')
            
            # 1. Detectar si el ejercicio usa peso corporal
            es_corporal = False
            if 'Corporal' in df_config.columns:
                ej_info = df_config[df_config['Ejercicio'] == ej_seleccionado]
                if not ej_info.empty and str(ej_info.iloc[0].get('Corporal', '')).upper() == 'SI':
                    es_corporal = True

            # 2. Obtener último peso corporal
            peso_usuario = float(df_perfil['Peso_Corporal'].iloc[-1]) if not df_perfil.empty and 'Peso_Corporal' in df_perfil.columns else 0.0

            # 3. Calcular el PESO REAL
            if es_corporal:
                df_graf['Peso_Real'] = df_graf['Peso'] + peso_usuario
            else:
                df_graf['Peso_Real'] = df_graf['Peso']
            
            df_graf['Volumen_Serie'] = df_graf['Peso_Real'] * df_graf['Repeticiones']
            
            df_agrupado = df_graf.groupby('Fecha_DT').agg(
                Peso_Maximo=('Peso_Real', 'max'),
                Volumen_Total=('Volumen_Serie', 'sum')
            ).reset_index()

            # --- TARJETAS DE RESUMEN ---
            mejor_peso_ever = df_agrupado['Peso_Maximo'].max()
            mejor_volumen_ever = df_agrupado['Volumen_Total'].max()
            ultimo_peso = df_agrupado.iloc[-1]['Peso_Maximo']
            ultimo_volumen = df_agrupado.iloc[-1]['Volumen_Total']

            st.divider()
            
            met1, met2 = st.columns(2)
            met1.markdown(f"""
            <div class='metric-container'>
                <div class='metric-value' style='color:#58a6ff'>{mejor_peso_ever} kg</div>
                <div class='metric-label'>Mejor Peso Movido (Real)</div>
                <small style='color:gray'>Último: {ultimo_peso} kg</small>
            </div>
            """, unsafe_allow_html=True)
            
            met2.markdown(f"""
            <div class='metric-container'>
                <div class='metric-value' style='color:#7ee787'>{int(mejor_volumen_ever)} kg</div>
                <div class='metric-label'>Volumen Récord (Real)</div>
                 <small style='color:gray'>Último: {int(ultimo_volumen)} kg</small>
            </div>
            """, unsafe_allow_html=True)

            st.write("") 
            
            # --- CONFIGURACIÓN PLOTLY ---
            dark_layout = dict(
                font=dict(family="Inter, sans-serif", color="#8b949e", size=12),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, zeroline=False, showline=False, tickformat="%d/%m"),
                yaxis=dict(showgrid=True, gridcolor="#2d333b", gridwidth=0.5, zeroline=False, showline=False),
                margin=dict(l=10, r=10, t=50, b=20),
                hovermode=False 
            )

            # --- GRÁFICA 1: PESO ---
            fig_peso = px.area(df_agrupado, x='Fecha_DT', y='Peso_Maximo', markers=True, 
                               title=f"⚡ Progresión de Cargas Reales (kg)")
            
            fig_peso.update_traces(
                line=dict(color='#58a6ff', width=3),
                marker=dict(size=8, color='#0e1117', line=dict(width=2, color='#58a6ff')),
                fillcolor='rgba(88, 166, 255, 0.15)' 
            )
            fig_peso.update_layout(dark_layout)
            fig_peso.update_yaxes(title_text="")
            fig_peso.update_xaxes(title_text="")

            st.plotly_chart(fig_peso, use_container_width=True, config={'staticPlot': True})
            
            # --- GRÁFICA 2: VOLUMEN ---
            fig_vol = px.bar(df_agrupado, x='Fecha_DT', y='Volumen_Total', 
                             title=f"🔋 Volumen de Trabajo Total Real")
            
            fig_vol.update_traces(
                marker_color='#7ee787', 
                marker_line_width=0 
            )
            fig_vol.update_layout(dark_layout)
            fig_vol.update_yaxes(title_text="")
            fig_vol.update_xaxes(title_text="")

            st.plotly_chart(fig_vol, use_container_width=True, config={'staticPlot': True})

# ==========================================
# PESTAÑA 3: AJUSTES (AÑADIR/ELIMINAR)
# ==========================================
with tab_config:
    st.markdown("### ⚙️ Ajustes y Gestión")
    
    # --- SECCIÓN DATOS PERSONALES ---
    with st.expander("👤 Mis Datos Personales", expanded=True):
        peso_actual = float(df_perfil['Peso_Corporal'].iloc[-1]) if not df_perfil.empty and 'Peso_Corporal' in df_perfil.columns else 75.0
        altura_actual = int(df_perfil['Altura'].iloc[-1]) if not df_perfil.empty and 'Altura' in df_perfil.columns else 175
        
        with st.form("form_perfil"):
            c1, c2 = st.columns(2)
            nuevo_peso = c1.number_input("Peso Corporal (kg)", value=peso_actual, step=0.5)
            nueva_altura = c2.number_input("Altura (cm)", value=altura_actual, step=1)
            
            if st.form_submit_button("💾 Guardar Datos", type="primary"):
                if ws_perfil is not None:
                    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
                    ws_perfil.append_row([fecha_hoy, nuevo_peso, nueva_altura])
                    st.success("¡Datos actualizados correctamente!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ No se encontró la hoja 'Datos_Personales' en tu Google Sheets. ¡Asegúrate de crearla!")

    st.markdown("#### Gestión de Rutinas")
    if df_config.empty:
        st.warning("No se pudo cargar la configuración de rutinas.")
    else:
        rutinas_existentes = df_config['Rutina'].unique().tolist()
        
        # --- SECCIÓN AÑADIR ---
        with st.expander("➕ Añadir nuevo ejercicio"):
            with st.form("form_add_ex", clear_on_submit=True):
                col1, col2 = st.columns(2)
                rut_add = col1.selectbox("¿A qué rutina lo añades?", rutinas_existentes)
                nombre_add = col2.text_input("Nombre del Ejercicio")
                
                musculos_base = ["Pecho", "Espalda", "Hombro", "Hombro Lateral", "Bíceps", "Tríceps", 
                                 "Cuádriceps", "Isquios", "Glúteo", "Gemelos", "Abdomen", "Salud Articular"]
                
                if 'Musculo' in df_config.columns:
                    musculos_existentes = [str(m).strip() for m in df_config['Musculo'].unique() if str(m).strip()]
                    lista_musculos = sorted(list(set(musculos_base + musculos_existentes)))
                else:
                    lista_musculos = sorted(musculos_base)
                
                col3, col4, col5 = st.columns(3)
                series_add = col3.number_input("Series Default", min_value=1, value=3, step=1)
                musculo_add = col4.selectbox("Músculo objetivo", lista_musculos)
                reps_add = col5.text_input("Reps Objetivo (ej. 8-12)")
                
                usa_corporal = st.checkbox("💪 ¿Este ejercicio utiliza el peso corporal? (Ej: Dominadas, Fondos)")
                
                if st.form_submit_button("Añadir al Plan", type="primary"):
                    if nombre_add:
                        es_corp_str = "SI" if usa_corporal else "NO"
                        nuevo_ejercicio = [rut_add, nombre_add, series_add, musculo_add, reps_add, es_corp_str]
                        ws_config.append_row(nuevo_ejercicio)
                        st.success(f"✅ '{nombre_add}' añadido a {rut_add}.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Rellena al menos el Nombre del Ejercicio.")
                        
        # --- SECCIÓN ELIMINAR ---
        with st.expander("🗑️ Eliminar ejercicio"):
            with st.form("form_del_ex"):
                st.warning("⚠️ Esta acción borrará el ejercicio de tu configuración actual.")
                rut_del = st.selectbox("Selecciona la rutina", rutinas_existentes, key="rut_del")
                
                ejs_en_rutina = df_config[df_config['Rutina'] == rut_del]['Ejercicio'].tolist()
                ej_del = st.selectbox("Ejercicio a eliminar", ejs_en_rutina)
                
                if st.form_submit_button("Eliminar permanentemente"):
                    idx = df_config[(df_config['Rutina'] == rut_del) & (df_config['Ejercicio'] == ej_del)].index
                    
                    if not idx.empty:
                        fila_sheet = int(idx[0]) + 2 
                        ws_config.delete_rows(fila_sheet)
                        st.success(f"🗑️ '{ej_del}' eliminado correctamente.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("No se encontró el ejercicio.")
