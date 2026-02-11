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
       
    


