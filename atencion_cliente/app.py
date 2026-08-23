"""
Interfaz web del asistente de atención al cliente de NovaFibra.

Ejecutar desde esta carpeta con:
    streamlit run app.py
"""

from __future__ import annotations

import uuid

import streamlit as st

from core.chatbot import (
    AgenteSoporte,
    ErrorConfiguracion,
    ErrorOpenAI,
    Turno,
)
from core.knowledge_base import ErrorBaseConocimiento
from core.prompts import MENSAJE_BIENVENIDA

st.set_page_config(page_title="Soporte NovaFibra", page_icon="💬", layout="centered")

EJEMPLOS = [
    "¿Cuánto cuesta el servicio premium?",
    "¿Y qué incluye?",
    "Mi internet va muy lento desde ayer",
    "¿Cuál es el estado de mi pedido NF-48120?",
    "Quiero hablar con un agente humano",
]


def iniciar_estado(reiniciar: bool = False) -> None:
    """Prepara (o reinicia) el estado de la sesión."""
    if reiniciar or "historial" not in st.session_state:
        st.session_state.historial = []
        st.session_state.tickets = []
        st.session_state.id_sesion = uuid.uuid4().hex[:10]


@st.cache_resource(show_spinner="Cargando agente...")
def obtener_agente() -> AgenteSoporte:
    """
    Crea el agente una sola vez por proceso.

    `cache_resource` evita releer la base de conocimiento y reconstruir el
    cliente de OpenAI en cada interacción de Streamlit.
    """
    return AgenteSoporte()


def barra_lateral() -> None:
    with st.sidebar:
        st.subheader("NovaFibra · Soporte")
        st.caption(
            "Asistente virtual de una empresa ficticia de internet de fibra "
            "óptica. Proyecto académico."
        )

        if st.button("Nueva conversación", use_container_width=True):
            iniciar_estado(reiniciar=True)
            st.rerun()

        st.divider()
        st.markdown("**Prueba con:**")
        for ejemplo in EJEMPLOS:
            st.markdown(f"- {ejemplo}")

        if st.session_state.get("tickets"):
            st.divider()
            st.markdown("**Tickets generados en esta sesión**")
            for ticket in st.session_state.tickets:
                st.code(ticket.como_texto(), language=None)


def render_historial() -> None:
    for turno in st.session_state.historial:
        with st.chat_message("user" if turno.rol == "user" else "assistant"):
            st.markdown(turno.contenido)


def main() -> None:
    iniciar_estado()

    st.title("💬 Soporte NovaFibra")
    st.caption("Asistente virtual de atención al cliente")

    barra_lateral()

    try:
        agente = obtener_agente()
    except ErrorConfiguracion as exc:
        st.error(str(exc))
        st.info(
            "Pasos: copia `.env.example` a `.env`, coloca tu clave de OpenAI en "
            "`OPENAI_API_KEY` y vuelve a ejecutar `streamlit run app.py`."
        )
        st.stop()
    except ErrorBaseConocimiento as exc:
        st.error(str(exc))
        st.stop()

    if not st.session_state.historial:
        with st.chat_message("assistant"):
            st.markdown(MENSAJE_BIENVENIDA)

    render_historial()

    mensaje = st.chat_input("Escribe tu consulta...")
    if not mensaje:
        return

    with st.chat_message("user"):
        st.markdown(mensaje)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Consultando..."):
                respuesta = agente.responder(
                    mensaje,
                    historial=st.session_state.historial,
                    id_sesion=st.session_state.id_sesion,
                )
        except ErrorOpenAI as exc:
            st.error(str(exc))
            return

        # Las consultas a sistemas internos se muestran para que se vea qué
        # información recibió el modelo antes de responder.
        for accion in respuesta.acciones:
            with st.status(accion.etiqueta, state="complete"):
                st.write(accion.resultado)

        st.markdown(respuesta.texto)

        if respuesta.ticket is not None:
            st.warning("Caso escalado a un agente humano")
            st.code(respuesta.ticket.como_texto(), language=None)
            st.session_state.tickets.append(respuesta.ticket)

    st.session_state.historial.append(Turno(rol="user", contenido=mensaje))
    st.session_state.historial.append(Turno(rol="assistant", contenido=respuesta.texto))


if __name__ == "__main__":
    main()
