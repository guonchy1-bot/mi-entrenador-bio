import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuración de la conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("tu_archivo_credenciales.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Entrenamientos_RayPeat")

st.set_page_config(page_title="Bio-Energy Workout Log", layout="centered")

st.title("🔋 Mi Log Bioenergético")
st.subheader("Entrenamiento de Hoy")

# Selector de Día
dia = st.selectbox("Selecciona el Entrenamiento", ["Lunes", "Martes", "Jueves", "Viernes"])
ws = sheet.worksheet(dia)

# Lista de ejercicios según tu rutina anterior (ejemplo Lunes)
ejercicios = {
    "Lunes": ["Pull Up (Weighted)", "Chin Up (Weighted)", "Seated Cable Row", "Bicep Curl", "Incline Curl"],
    "Martes": ["Shoulder Press", "Chest Press", "Triceps Dip", "Lateral Raise", "Triceps Extension"]
    # ... añade el resto
}

with st.form("registro_entreno"):
    st.write(f"### {dia}")
    ejercicio_sel = st.selectbox("Ejercicio", ejercicios[dia])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        serie = st.number_input("Serie", min_value=1, step=1)
    with col2:
        reps = st.number_input("Reps", min_value=1, step=1)
    with col3:
        peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5)
    
    notas = st.text_input("Notas (sensaciones, fatiga...)")
    submit = st.form_submit_button("Guardar en Google Sheets")

    if submit:
        nueva_fila = [datetime.now().strftime("%Y-%m-%d %H:%M"), ejercicio_sel, serie, reps, peso, notas]
        ws.append_row(nueva_fila)
        st.success("✅ ¡Guardado con éxito!")