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

st.markdown(
    """
    <style>
    body {background-color:#ffffff;}
    .stButton>button {background-color:#d2e9e2;color:#6b4e16;}
    .stTabs [data-baseweb="tab"] {font-weight:bold;color:#6b4e16;}
    </style>
    """,
    unsafe_allow_html=True,
)


# Funciones de carga y guardado
@st.cache_data
def cargar_agenda():
    try:
        return pd.read_csv("agenda.csv")
    except FileNotFoundError:
        return pd.DataFrame(
            columns=[
                "Participante",
                "Fecha",
                "Hora",
                "Sesión",
                "Tipo de sesión",
                "Secuencia",
            ]
        )


def guardar_agenda(df):
    df.to_csv("agenda.csv", index=False)


@st.cache_data
def cargar_secuencias():
    try:
        return pd.read_csv("secuencias.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["Participante", "Secuencia"])


def guardar_secuencias(df):
    df.to_csv("secuencias.csv", index=False)


# Función para calendario visual
def crear_calendario_interactivo(
    df, fecha_col="Fecha", hora_col="Hora", titulo_evento="Sesión"
):
    eventos = []
    df = df.copy()
    df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")

    for _, row in df.iterrows():
        fecha = row[fecha_col].strftime("%Y-%m-%d")
        hora = (
            row[hora_col]
            if isinstance(row[hora_col], str)
            else row[hora_col].strftime("%H:%M")
        )
        evento = {
            "title": f"{row[titulo_evento]} - {row['Participante']}\n{hora}",
            "start": f"{fecha}T{hora}",
            "end": f"{fecha}T{hora}",
        }
        if row[titulo_evento] == "PERIODO DE LAVADO":
            evento["color"] = "#cccccc"
        eventos.append(evento)

    calendar_options = {
        "initialView": "dayGridMonth",
        "locale": "es",
        "height": 600,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay",
        },
    }

    return calendar(events=eventos, options=calendar_options)


# Cargar datos
if "agenda" not in st.session_state:
    st.session_state.agenda = cargar_agenda()
if "secuencias" not in st.session_state:
    st.session_state.secuencias = cargar_secuencias()

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
            fecha = st.date_input("Fecha de la primera sesión")
        with col3:
            hora = st.time_input("Hora de sesión", value=time(8, 0))

        confirmar = st.checkbox("Confirmar programación si existen choques")

        if st.form_submit_button("Agregar participante"):
            if participante in st.session_state.agenda["Participante"].unique():
                st.error("El participante ya tiene agenda registrada.")
            elif participante not in st.session_state.secuencias["Participante"].values:
                st.error(
                    "Debe asignar la secuencia en la pestaña de logística antes de agendar."
                )
            else:
                orden = [
                    ("Sesión 1", "larga"),
                    ("Sesión 2", "corta"),
                    ("Sesión 3", "larga"),
                    ("PERIODO DE LAVADO", ""),
                    ("Sesión 4", "larga"),
                    ("Sesión 5", "corta"),
                    ("Sesión 6", "larga"),
                ]

                nuevas_filas = []
                conflictos = []
                exceso = False
                for idx, (ses, tipo) in enumerate(orden):
                    fecha_sesion = fecha + timedelta(weeks=idx)
                    fecha_str = fecha_sesion.strftime("%Y-%m-%d")
                    hora_str = hora.strftime("%H:%M")
                    existentes = st.session_state.agenda[
                        (st.session_state.agenda["Fecha"] == fecha_str)
                        & (st.session_state.agenda["Hora"] == hora_str)
                    ]
                    if len(existentes) >= 3:
                        exceso = True
                        break
                    if len(existentes) > 0:
                        conflictos.append(f"{fecha_str} {hora_str}")
                    nuevas_filas.append(
                        {
                            "Participante": participante,
                            "Fecha": fecha_str,
                            "Hora": hora_str,
                            "Sesión": ses,
                            "Tipo de sesión": tipo,
                            "Secuencia": st.session_state.secuencias.set_index(
                                "Participante"
                            ).loc[
                                participante,
                                "Secuencia",
                            ],
                        }
                    )

                if exceso:
                    st.error(
                        "Existe un horario con más de 3 participantes. Cambie la hora."
                    )
                elif conflictos and not confirmar:
                    st.warning(
                        "Hay choques con otros participantes en: "
                        + ", ".join(conflictos)
                    )
                    st.stop()
                else:
                    st.session_state.agenda = pd.concat(
                        [st.session_state.agenda, pd.DataFrame(nuevas_filas)],
                        ignore_index=True,
                    )
                    guardar_agenda(st.session_state.agenda)
                    st.success("Sesiones agregadas correctamente.")
                    st.rerun()

    st.subheader("Agenda programada")
    with st.expander("Ver tabla de agenda"):
        df_vis = st.session_state.agenda.copy()
        df_vis["Fecha"] = pd.to_datetime(df_vis["Fecha"]).dt.strftime("%A %d de %B, %Y")
        if "Secuencia" in df_vis.columns:
            df_vis = df_vis.drop(columns=["Secuencia"])
        df_vis = df_vis[df_vis["Sesión"] != "PERIODO DE LAVADO"]
        st.dataframe(df_vis, use_container_width=True, hide_index=True)

    with st.expander("Buscar participante"):
        buscar = st.text_input("Folio a buscar")
        if buscar:
            filtrado = df_vis[df_vis["Participante"].astype(str).str.contains(buscar)]
            st.dataframe(filtrado, use_container_width=True, hide_index=True)

    st.markdown("### Calendario visual")
    if not st.session_state.agenda.empty:
        cal_data = crear_calendario_interactivo(st.session_state.agenda)
        if cal_data and cal_data.get("event"):
            ev = cal_data["event"]
            with st.expander("Detalle de evento"):
                st.write(ev)
                if st.button("Eliminar", key=f"del_{ev['title']}"):
                    confirm_elim = st.checkbox(
                        "Confirmar eliminación", key=f"conf_{ev['title']}"
                    )
                    if confirm_elim:
                        st.session_state.agenda = st.session_state.agenda[
                            ~(
                                (st.session_state.agenda["Fecha"] == ev["start"][:10])
                                & (
                                    st.session_state.agenda["Hora"]
                                    == ev["start"][11:16]
                                )
                                & (
                                    st.session_state.agenda["Participante"]
                                    == ev["title"].split(" - ")[-1]
                                )
                            )
                        ]
                        guardar_agenda(st.session_state.agenda)
                        st.rerun()
    else:
        st.info("No hay sesiones aún para mostrar en el calendario.")

# ---------------- TAB 2: LOGÍSTICA ----------------
with tabs[1]:
    st.header("Logística de preparación de bebidas")

    with st.expander("Asignar secuencia"):
        with st.form("form_secuencia"):
            col1, col2 = st.columns(2)
            with col1:
                participante_seq = st.text_input(
                    "Folio del participante", key="seq_part"
                )
            with col2:
                secuencia_nueva = st.selectbox("Secuencia", ["AB", "BA"], key="seq_sel")
            if st.form_submit_button("Guardar secuencia"):
                df = st.session_state.secuencias
                if participante_seq in df["Participante"].values:
                    st.session_state.secuencias.loc[
                        df["Participante"] == participante_seq, "Secuencia"
                    ] = secuencia_nueva
                else:
                    st.session_state.secuencias = pd.concat(
                        [
                            df,
                            pd.DataFrame(
                                [
                                    {
                                        "Participante": participante_seq,
                                        "Secuencia": secuencia_nueva,
                                    }
                                ]
                            ),
                        ],
                        ignore_index=True,
                    )
                guardar_secuencias(st.session_state.secuencias)
                st.success("Secuencia registrada")
                st.rerun()
        st.dataframe(
            st.session_state.secuencias, hide_index=True, use_container_width=True
        )

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
            "Sesión 5": (8, 7),
        }
        agenda = agenda.copy()
        agenda = agenda.merge(
            st.session_state.secuencias, on="Participante", how="left"
        )
        agenda["Fecha"] = pd.to_datetime(agenda["Fecha"])
        for _, row in agenda.iterrows():
            sesion = row["Sesión"]
            if sesion in sesiones_validas:
                participante = row["Participante"]
                fecha_sesion = row["Fecha"]
                frascos, bebidas = sesiones_validas[sesion]
                bebida_tipo = tipo_bebida(row["Secuencia"], sesion)

                fecha_est = obtener_dia_habil_previo(fecha_sesion, 3)
                actividades.append(
                    {
                        "Participante": participante,
                        "Sesión": sesion,
                        "Fecha logística": fecha_est,
                        "Hora": "08:00",
                        "Actividad": f"Esterilizar {frascos} frascos ({bebida_tipo})",
                    }
                )

                fecha_cb = obtener_dia_habil_previo(fecha_sesion, 2)
                actividades.append(
                    {
                        "Participante": participante,
                        "Sesión": sesion,
                        "Fecha logística": fecha_cb,
                        "Hora": "08:00",
                        "Actividad": f"Preparar coldbrew ({bebida_tipo})",
                    }
                )

                fecha_pb = obtener_dia_habil_previo(fecha_sesion, 1)
                actividades.append(
                    {
                        "Participante": participante,
                        "Sesión": sesion,
                        "Fecha logística": fecha_pb,
                        "Hora": "08:00",
                        "Actividad": f"Preparar {bebidas} bebidas ({bebida_tipo})",
                    }
                )

        return pd.DataFrame(actividades)

    if st.session_state.agenda.empty:
        st.warning("Agrega sesiones en la pestaña de agenda para generar logística.")
    else:
        cronograma = generar_logistica(st.session_state.agenda)
        st.dataframe(cronograma, use_container_width=True, hide_index=True)

        st.markdown("### Calendario de actividades logísticas")
        crear_calendario_interactivo(
            cronograma, fecha_col="Fecha logística", titulo_evento="Actividad"
        )
