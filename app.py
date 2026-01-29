import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# 1. FUNCIÓN DE CONEXIÓN SEGURA
def conectar_google_sheets():
    # Definimos el acceso
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Leemos las credenciales desde los "Secrets" de Streamlit
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    # Autorizamos y abrimos el archivo
    client = gspread.authorize(creds)
    
    # IMPORTANTE: Asegúrate de que el nombre del Excel sea este exactamente
    return client.open("Entrenamientos_RayPeat")

# 2. CONFIGURACIÓN DE LA INTERFAZ
st.set_page_config(page_title="Bio-Log Workout", page_icon="🔋")

st.title("🔋 Mi entrenamiento")
st.write("Registra tus marcas siguiendo los principios de Ray Peat.")

# 3. DEFINICIÓN DE LA RUTINA
rutina = {
    "Espalda-biceps": ["Pull Up (Weighted)", "Chin Up (Weighted)", "Seated Cable Row", "Bicep Curl (Barbell)", "Incline Curl"],
    "Pecho-triceps-hombro": ["Shoulder Press", "Chest Press", "Triceps Dip", "Lateral Raise", "Triceps Extension", "Tríceps Unilateral"],
    "Pierna": ["Full Squat", "Zancada", "Lying Leg Curl", "Seated Calf Raise", "Standing Calf Raise"],
    "Tren superior": ["Incline Bench Press", "Seated Cable Row (Wide)", "Lateral Raise", "Preacher Curl", "Single Arm Triceps Pushdown"]
}

# 4. SELECTORES DE DÍA Y EJERCICIO
# Usamos nombres limpios para las pestañas del Excel
dia_seleccionado = st.selectbox("Día de entrenamiento", list(rutina.keys()))
ejercicio_seleccionado = st.selectbox("Ejercicio", rutina[dia_seleccionado])

# 5. FORMULARIO DE REGISTRO
with st.form("registro_serie"):
    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5, format="%.2f")
        serie = st.number_input("Serie nº", min_value=1, step=1)
    with col2:
        reps = st.number_input("Repeticiones", min_value=1, step=1)
        rpe = st.slider("Esfuerzo (RPE)", 1, 10, 8)
    
    notas = st.text_input("Notas (CO2, temperatura, sensaciones...)")
    
    boton_guardar = st.form_submit_button("GUARDAR EN EXCEL")

    if boton_guardar:
        try:
            # Conectamos dentro del botón para evitar errores de carga
            spreadsheet = conectar_google_sheets()
            
            # Buscamos la pestaña (Hoja) del día seleccionado
            worksheet = spreadsheet.worksheet(dia_seleccionado)
            
            # Preparamos los datos
            fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            datos_a_insertar = [fecha_hora, ejercicio_seleccionado, serie, reps, peso, rpe, notas]
            
            # Insertamos la fila
            worksheet.append_row(datos_a_insertar)
            
            st.success(f"✅ ¡Guardado! {ejercicio_seleccionado} - Serie {serie}")
            st.balloons()
            
        except Exception as e:
            st.error(f"Error al guardar: {e}")
            st.info("Revisa que el Excel tenga pestañas llamadas: Lunes, Martes, Jueves, Viernes")

# 6. HISTORIAL (OPCIONAL)
if st.button("Ver historial de hoy"):
    try:
        spreadsheet = conectar_google_sheets()
        worksheet = spreadsheet.worksheet(dia_seleccionado)
        df = pd.DataFrame(worksheet.get_all_records())
        if not df.empty:
            st.table(df.tail(5))
        else:
            st.write("No hay datos todavía para este día.")
    except:
        st.write("Cargando historial...")

