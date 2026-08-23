"""
Pruebas de la interfaz de Streamlit.

Usan `streamlit.testing.v1.AppTest`, que ejecuta `app.py` en el mismo proceso
sin navegador ni servidor, y permite comprobar que el script corre sin
excepciones y que los widgets se comportan como se espera.

El cliente de OpenAI se sustituye por uno falso, de modo que el flujo de la
interfaz se verifica sin clave de API ni llamadas reales.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from core import chatbot  # noqa: E402

RUTA_APP = str(RAIZ / "app.py")


class RespuestaFalsa:
    def __init__(self, texto: str) -> None:
        self.output_text = texto


class ClienteFalso:
    def __init__(self, texto: str) -> None:
        self.responses = self
        self._texto = texto

    def create(self, **kwargs):
        return RespuestaFalsa(self._texto)


class TestInterfaz(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        self._original = chatbot.crear_cliente_openai

    def tearDown(self):
        chatbot.crear_cliente_openai = self._original
        st.cache_resource.clear()

    def _parchear(self, texto: str):
        chatbot.crear_cliente_openai = lambda: ClienteFalso(texto)

    def _sin_excepciones(self, at: AppTest):
        """`at.exception` es una lista de elementos, vacía cuando todo fue bien."""
        if len(at.exception) > 0:
            self.fail("excepción no controlada: " + "; ".join(e.value for e in at.exception))

    def test_sin_clave_muestra_error_controlado(self):
        def sin_clave():
            raise chatbot.ErrorConfiguracion("No se encontró la variable OPENAI_API_KEY.")

        chatbot.crear_cliente_openai = sin_clave

        at = AppTest.from_file(RUTA_APP, default_timeout=60).run()

        self._sin_excepciones(at)
        self.assertTrue(at.error, "se esperaba un mensaje de error visible")
        self.assertIn("OPENAI_API_KEY", at.error[0].value)

    def test_arranque_normal(self):
        self._parchear("Hola, ¿en qué te ayudo?")
        at = AppTest.from_file(RUTA_APP, default_timeout=60).run()

        self._sin_excepciones(at)
        self.assertFalse(at.error)
        self.assertIn("Soporte NovaFibra", at.title[0].value)
        self.assertTrue(at.chat_input, "no se renderizó el campo de chat")

    def test_conversacion_y_persistencia_del_historial(self):
        self._parchear("El plan Fibra Premium cuesta 899 MXN al mes.")
        at = AppTest.from_file(RUTA_APP, default_timeout=60).run()

        at.chat_input[0].set_value("¿Cuánto cuesta el plan premium?").run()

        self._sin_excepciones(at)
        self.assertEqual(len(at.session_state["historial"]), 2)
        self.assertEqual(at.session_state["historial"][0].rol, "user")
        self.assertEqual(at.session_state["historial"][1].rol, "assistant")
        self.assertIn("899", at.session_state["historial"][1].contenido)

    def test_escalamiento_genera_ticket_visible(self):
        self._parchear("Entiendo tu situación.")
        at = AppTest.from_file(RUTA_APP, default_timeout=60).run()

        at.chat_input[0].set_value("Quiero hablar con un agente humano").run()

        self._sin_excepciones(at)
        self.assertTrue(at.warning, "se esperaba el aviso de escalamiento")
        self.assertEqual(len(at.session_state["tickets"]), 1)
        self.assertTrue(at.session_state["tickets"][0].folio.startswith("SOP-"))

    def test_boton_nueva_conversacion_limpia_el_historial(self):
        self._parchear("Respuesta.")
        at = AppTest.from_file(RUTA_APP, default_timeout=60).run()
        at.chat_input[0].set_value("hola").run()
        self.assertEqual(len(at.session_state["historial"]), 2)

        at.sidebar.button[0].click().run()

        self._sin_excepciones(at)
        self.assertEqual(at.session_state["historial"], [])
        self.assertEqual(at.session_state["tickets"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
