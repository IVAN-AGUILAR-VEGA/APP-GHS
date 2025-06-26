import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from streamlit_calendar import calendar
import locale

# Configurar idioma local
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_TIME, "es_ES")
    except:
        pass

st.set_page_config(page_title="Gestión clínica", layout="wide")

# Funciones de carga y guardado
@st.cache_data
def cargar_agenda():
    try:
        return pd.read_csv("agenda.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["Participante", "Fecha", "Hora", "Sesión", "Tipo de sesión", "Secuencia"])

def guardar_agenda(df):
    df.to_csv("agenda.csv", index=False)

# Función para calendario visual
def crear_calendario_interactivo(df, fecha_col="Fecha", hora_col="Hora", titulo_evento="Sesión"):
    eventos = []
    df = df.copy()
    df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")

    for _, row in df.iterrows():
        fecha = row[fecha_col].strftime("%Y-%m-%d")
        hora = row[hora_col] if isinstance(row[hora_col], str) else row[hora_col].strftime("%H:%M")
        eventos.append({
            "title": f"{row[titulo_evento]} - {row['Participante']}",
            "start": f"{fecha}T{hora}",
            "end": f"{fecha}T{hora}"
        })

    calendar_options = {
        "initialView": "dayGridMonth",
        "locale": "es",
        "height": 600,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        }
    }

    calendar(events=eventos, options=calendar_options)

# Cargar datos
if "agenda" not in st.session_state:
    st.session_state.agenda = cargar_agenda()

# Tabs principales
tabs = st.tabs(["📅 Agenda de participantes", "🧃 Logística de bebidas"])

# ---------------- TAB 1: AGENDA ----------------
with tabs[0]:
    st.header("Agenda de participantes")

    # Formulario para agregar
    with st.form("form_agregar_agenda"):
        col1, col2, col3 = st.columns(3)
        with col1:
            participante = st.text_input("Folio del participante")
        with col2:
            fecha = st.date_input("Fecha de sesión")
        with col3:
            hora = st.time_input("Hora de sesión", value=time(8, 0))

        sesion = st.selectbox("Sesión", ["Sesión 1", "Sesión 2", "Sesión 3", "Sesión 4", "Sesión 5", "Sesión 6"])
        tipo = st.selectbox("Tipo de sesión", ["larga", "corta"])
        secuencia = st.selectbox("Secuencia", ["AB", "BA"])

        if st.form_submit_button("Agregar sesión"):
            nueva_fila = {
                "Participante": participante,
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Hora": hora.strftime("%H:%M"),
                "Sesión": sesion,
                "Tipo de sesión": tipo,
                "Secuencia": secuencia
            }
            st.session_state.agenda = pd.concat([st.session_state.agenda, pd.DataFrame([nueva_fila])], ignore_index=True)
            guardar_agenda(st.session_state.agenda)
            st.success("Sesión agregada correctamente.")
            st.rerun()

    st.subheader("Agenda programada")
    st.dataframe(st.session_state.agenda, use_container_width=True)

    st.markdown("### Calendario visual")
    if not st.session_state.agenda.empty:
        crear_calendario_interactivo(st.session_state.agenda)
    else:
        st.info("No hay sesiones aún para mostrar en el calendario.")

# ---------------- TAB 2: LOGÍSTICA ----------------
with tabs[1]:
    st.header("Logística de preparación de bebidas")

    def tipo_bebida(secuencia, sesion):
        if sesion in ["Sesión 1", "Sesión 2", "Sesión 3"]:
            return "Intervención" if secuencia == "AB" else "Control"
        elif sesion in ["Sesión 4", "Sesión 5", "Sesión 6"]:
            return "Control" if secuencia == "AB" else "Intervención"
        return ""

    def obtener_dia_habil_previo(fecha, dias):
        fecha_resultado = fecha
        while dias > 0:
            fecha_resultado -= timedelta(days=1)
            if fecha_resultado.weekday() < 5:
                dias -= 1
        return fecha_resultado

    def generar_logistica(agenda):
        actividades = []
        sesiones_validas = {
            "Sesión 1": (9, 8),
            "Sesión 2": (8, 7),
            "Sesión 4": (9, 8),
            "Sesión 5": (8, 7)
        }
        agenda = agenda.copy()
        agenda["Fecha"] = pd.to_datetime(agenda["Fecha"])
        for _, row in agenda.iterrows():
            sesion = row["Sesión"]
            if sesion in sesiones_validas:
                participante = row["Participante"]
                fecha_sesion = row["Fecha"]
                frascos, bebidas = sesiones_validas[sesion]
                bebida_tipo = tipo_bebida(row["Secuencia"], sesion)

                fecha_est = obtener_dia_habil_previo(fecha_sesion, 3)
                actividades.append({
                    "Participante": participante,
                    "Sesión": sesion,
                    "Fecha logística": fecha_est,
                    "Hora": "08:00",
                    "Actividad": f"Esterilizar {frascos} frascos ({bebida_tipo})"
                })

                fecha_cb = obtener_dia_habil_previo(fecha_sesion, 2)
                actividades.append({
                    "Participante": participante,
                    "Sesión": sesion,
                    "Fecha logística": fecha_cb,
                    "Hora": "08:00",
                    "Actividad": f"Preparar coldbrew ({bebida_tipo})"
                })

                fecha_pb = obtener_dia_habil_previo(fecha_sesion, 1)
                actividades.append({
                    "Participante": participante,
                    "Sesión": sesion,
                    "Fecha logística": fecha_pb,
                    "Hora": "08:00",
                    "Actividad": f"Preparar {bebidas} bebidas ({bebida_tipo})"
                })

        return pd.DataFrame(actividades)

    if st.session_state.agenda.empty:
        st.warning("Agrega sesiones en la pestaña de agenda para generar logística.")
    else:
        cronograma = generar_logistica(st.session_state.agenda)
        st.dataframe(cronograma, use_container_width=True)

        st.markdown("### Calendario de actividades logísticas")
        crear_calendario_interactivo(cronograma, fecha_col="Fecha logística", titulo_evento="Actividad")
