"""
Pruebas del agente de soporte.

Usan un cliente de OpenAI falso, de modo que se puede verificar toda la lógica
—base de conocimiento, prompt, acciones simuladas, historial y escalamiento—
sin clave de API ni consumo de tokens. Lo único que estas pruebas NO cubren es
la llamada real a la API.

Ejecutar desde la carpeta del proyecto:
    python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import acciones, escalamiento  # noqa: E402
from core.chatbot import AgenteSoporte, Turno, extraer_texto  # noqa: E402
from core.knowledge_base import (  # noqa: E402
    ErrorBaseConocimiento,
    cargar_base_conocimiento,
)
from core.prompts import MARCADOR_ESCALAMIENTO, construir_prompt_sistema  # noqa: E402


class RespuestaFalsa:
    def __init__(self, texto: str) -> None:
        self.output_text = texto


class ClienteFalso:
    """Sustituto del cliente de OpenAI: registra la llamada y devuelve un texto fijo."""

    def __init__(self, texto: str = "Respuesta de prueba.") -> None:
        self.responses = self
        self._texto = texto
        self.llamadas: list[dict] = []

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        return RespuestaFalsa(self._texto)

    @property
    def ultima(self) -> dict:
        return self.llamadas[-1]


def agente_de_prueba(texto: str = "Respuesta de prueba.") -> tuple[AgenteSoporte, ClienteFalso]:
    cliente = ClienteFalso(texto)
    base = cargar_base_conocimiento()
    return AgenteSoporte(cliente=cliente, modelo="modelo-de-prueba", base=base), cliente


class TestBaseConocimiento(unittest.TestCase):
    def test_carga_y_valida(self):
        base = cargar_base_conocimiento()
        self.assertEqual(base.nombre_empresa, "NovaFibra")
        self.assertGreaterEqual(len(base.servicios), 3)
        self.assertGreaterEqual(len(base.preguntas_frecuentes), 5)

    def test_ruta_inexistente(self):
        with self.assertRaises(ErrorBaseConocimiento):
            cargar_base_conocimiento("no_existe.json")

    def test_precios_presentes_en_el_texto(self):
        texto = cargar_base_conocimiento().como_texto()
        self.assertIn("Fibra Premium", texto)
        self.assertIn("899 MXN/mes", texto)
        self.assertIn("CRITERIOS DE ESCALAMIENTO", texto)

    def test_buscar_servicio(self):
        base = cargar_base_conocimiento()
        servicio = base.buscar_servicio("me interesa el plan fibra plus")
        self.assertIsNotNone(servicio)
        self.assertEqual(servicio["precio_mensual_mxn"], 599)
        self.assertIsNone(base.buscar_servicio("hola buenas tardes"))


class TestPrompt(unittest.TestCase):
    def test_contiene_reglas_y_contexto(self):
        prompt = construir_prompt_sistema(cargar_base_conocimiento())
        self.assertIn("NovaFibra", prompt)
        self.assertIn(MARCADOR_ESCALAMIENTO, prompt)
        self.assertIn("INFORMACIÓN DE LA EMPRESA", prompt)
        self.assertIn("no lo inventes", prompt.lower())


class TestAccionesSimuladas(unittest.TestCase):
    def test_detecta_consulta_de_pedido(self):
        detectadas = acciones.detectar_acciones("¿Cómo va mi pedido NF-48120?", "s1")
        self.assertTrue(any("pedido" in a.etiqueta.lower() for a in detectadas))

    def test_detecta_consulta_de_cuenta(self):
        detectadas = acciones.detectar_acciones("¿Cuál es mi saldo?", "s1")
        self.assertTrue(any("clientes" in a.etiqueta.lower() for a in detectadas))

    def test_detecta_falla(self):
        detectadas = acciones.detectar_acciones("mi internet va lento", "s1")
        self.assertTrue(any("diagnóstico" in a.etiqueta.lower() for a in detectadas))

    def test_sin_disparadores_no_hay_acciones(self):
        self.assertEqual(acciones.detectar_acciones("¿Qué planes ofrecen?", "s1"), [])

    def test_resultados_deterministas(self):
        primera = acciones.consultar_pedido("48120")
        segunda = acciones.consultar_pedido("48120")
        self.assertEqual(primera.resultado, segunda.resultado)
        self.assertNotEqual(primera.resultado, acciones.consultar_pedido("99999").resultado)


class TestEscalamiento(unittest.TestCase):
    def test_regla_legal(self):
        veredicto = escalamiento.evaluar_mensaje("Voy a poner una demanda contra ustedes")
        self.assertTrue(veredicto.escalar)
        self.assertIn("legal", veredicto.motivo.lower())

    def test_peticion_de_humano(self):
        self.assertTrue(escalamiento.evaluar_mensaje("quiero hablar con una persona").escalar)

    def test_consulta_normal_no_escala(self):
        self.assertFalse(escalamiento.evaluar_mensaje("¿cuánto cuesta Fibra Plus?").escalar)

    def test_limpieza_del_marcador(self):
        crudo = f"Tu caso necesita revisión.\n\n{MARCADOR_ESCALAMIENTO}"
        limpio = escalamiento.limpiar_marcador(crudo)
        self.assertNotIn(MARCADOR_ESCALAMIENTO, limpio)
        self.assertEqual(limpio, "Tu caso necesita revisión.")

    def test_ticket_reproducible_y_con_prioridad(self):
        t1 = escalamiento.crear_ticket("Asunto legal o regulatorio", "demanda")
        t2 = escalamiento.crear_ticket("Asunto legal o regulatorio", "demanda")
        self.assertEqual(t1.folio, t2.folio)
        self.assertTrue(t1.folio.startswith("SOP-"))
        self.assertEqual(t1.prioridad, "Alta")
        self.assertEqual(escalamiento.crear_ticket("Duda general", "x").prioridad, "Media")


class TestExtraerTexto(unittest.TestCase):
    def test_usa_output_text(self):
        self.assertEqual(extraer_texto(RespuestaFalsa("hola")), "hola")

    def test_recorre_output_cuando_no_hay_atajo(self):
        class Parte:
            type = "output_text"
            text = "desde output"

        class Mensaje:
            type = "message"
            content = [Parte()]

        class Respuesta:
            output_text = ""
            output = [Mensaje()]

        self.assertEqual(extraer_texto(Respuesta()), "desde output")


class TestFlujoDelAgente(unittest.TestCase):
    def test_respuesta_simple(self):
        agente, cliente = agente_de_prueba("El plan Fibra Premium cuesta 899 MXN al mes.")
        r = agente.responder("¿Cuánto cuesta el plan premium?")
        self.assertIn("899", r.texto)
        self.assertFalse(r.escalado)
        self.assertEqual(cliente.ultima["model"], "modelo-de-prueba")
        self.assertIn("NovaFibra", cliente.ultima["instructions"])

    def test_historial_se_envia_al_modelo(self):
        agente, cliente = agente_de_prueba("Incluye router Wi-Fi 7 y NovaTV.")
        historial = [
            Turno(rol="user", contenido="¿Cuánto cuesta el servicio premium?"),
            Turno(rol="assistant", contenido="Cuesta 899 MXN al mes."),
        ]
        agente.responder("¿Y qué incluye?", historial=historial)

        entrada = cliente.ultima["input"]
        self.assertEqual(len(entrada), 3)
        self.assertEqual(entrada[0]["role"], "user")
        self.assertIn("premium", entrada[0]["content"].lower())
        self.assertEqual(entrada[1]["role"], "assistant")
        self.assertEqual(entrada[-1]["content"], "¿Y qué incluye?")

    def test_acciones_se_inyectan_en_el_mensaje(self):
        agente, cliente = agente_de_prueba("Tu pedido está en camino.")
        r = agente.responder("¿Cómo va mi pedido NF-48120?")
        self.assertTrue(r.acciones)
        self.assertIn("DATOS CONSULTADOS", cliente.ultima["input"][-1]["content"])
        self.assertIn("NF-48120", cliente.ultima["input"][-1]["content"])

    def test_escalamiento_por_regla_determinista(self):
        agente, _ = agente_de_prueba("Entiendo tu situación.")
        r = agente.responder("Quiero hablar con un agente humano")
        self.assertTrue(r.escalado)
        self.assertIsNotNone(r.ticket)
        self.assertIn("agente humano", r.texto)
        self.assertIn("ticket de soporte", r.texto.lower())

    def test_escalamiento_pedido_por_el_modelo(self):
        agente, _ = agente_de_prueba(f"No dispongo de ese dato.\n{MARCADOR_ESCALAMIENTO}")
        r = agente.responder("¿Tienen cobertura en Tijuana?")
        self.assertTrue(r.escalado)
        self.assertNotIn(MARCADOR_ESCALAMIENTO, r.texto)

    def test_historial_se_recorta(self):
        from core.chatbot import TURNOS_DE_CONTEXTO

        agente, cliente = agente_de_prueba()
        largo = [Turno(rol="user", contenido=f"mensaje {i}") for i in range(40)]
        agente.responder("último", historial=largo)
        self.assertEqual(len(cliente.ultima["input"]), TURNOS_DE_CONTEXTO + 1)

    def test_mensaje_vacio(self):
        agente, _ = agente_de_prueba()
        with self.assertRaises(ValueError):
            agente.responder("   ")

    def test_error_de_api_se_envuelve(self):
        from core.chatbot import ErrorOpenAI

        class ClienteRoto:
            def __init__(self):
                self.responses = self

            def create(self, **kwargs):
                raise RuntimeError("503 service unavailable")

        agente = AgenteSoporte(
            cliente=ClienteRoto(), modelo="m", base=cargar_base_conocimiento()
        )
        with self.assertRaises(ErrorOpenAI):
            agente.responder("hola")


if __name__ == "__main__":
    unittest.main(verbosity=2)
