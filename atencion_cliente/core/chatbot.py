"""
Orquestación del agente de soporte.

Reúne las piezas del sistema: base de conocimiento, prompt, acciones simuladas,
escalamiento e historial, y resuelve un turno de conversación contra la API de
OpenAI.

El cliente de OpenAI se recibe por inyección de dependencia. Eso permite
ejercitar todo el flujo en las pruebas con un cliente falso, sin consumir
tokens ni necesitar una clave.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from .acciones import AccionSimulada, detectar_acciones
from .escalamiento import (
    MENSAJE_ESCALAMIENTO,
    Ticket,
    crear_ticket,
    evaluar_mensaje,
    limpiar_marcador,
    respuesta_contiene_marcador,
)
from .knowledge_base import BaseConocimiento, cargar_base_conocimiento
from .prompts import construir_prompt_sistema, formatear_datos_consultados

MODELO_POR_DEFECTO = "gpt-5.6-luna"
MAX_TOKENS_RESPUESTA = 700

# Número de turnos previos que se envían al modelo. Acota el costo por llamada
# sin perder el hilo de la conversación en un chat de soporte, donde las
# referencias suelen apuntar a los últimos mensajes.
TURNOS_DE_CONTEXTO = 12


class ErrorConfiguracion(Exception):
    """Falta configuración imprescindible, como la clave de API."""


class ErrorOpenAI(Exception):
    """La llamada a la API de OpenAI falló."""


class ClienteOpenAI(Protocol):
    """Superficie mínima del cliente de OpenAI que usa este proyecto."""

    responses: Any


@dataclass
class Turno:
    """Un mensaje de la conversación."""

    rol: str  # "user" | "assistant"
    contenido: str


@dataclass
class RespuestaAgente:
    """Resultado completo de un turno, incluido lo que la interfaz debe mostrar."""

    texto: str
    acciones: list[AccionSimulada] = field(default_factory=list)
    ticket: Ticket | None = None

    @property
    def escalado(self) -> bool:
        return self.ticket is not None


def crear_cliente_openai() -> ClienteOpenAI:
    """
    Construye el cliente oficial de OpenAI a partir de OPENAI_API_KEY.

    La clave se lee del entorno; si existe un archivo .env se carga primero.
    Nunca se escribe la clave en el código ni se registra en los logs.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        # python-dotenv es opcional: si la variable ya está en el entorno,
        # el proyecto funciona igual.
        pass

    clave = os.getenv("OPENAI_API_KEY", "").strip()
    if not clave:
        raise ErrorConfiguracion(
            "No se encontró la variable de entorno OPENAI_API_KEY. "
            "Copia .env.example a .env y coloca ahí tu clave, o expórtala en la terminal."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ErrorConfiguracion(
            "El paquete 'openai' no está instalado. Ejecuta: pip install -r requirements.txt"
        ) from exc

    return OpenAI(api_key=clave)


def extraer_texto(respuesta: Any) -> str:
    """
    Obtiene el texto de una respuesta de la Responses API.

    El SDK expone `output_text` como atajo, pero la forma documentada y estable
    es recorrer `output` buscando los fragmentos de tipo `output_text`. Se
    intenta primero el atajo y se recurre al recorrido si no está disponible.
    """
    texto = getattr(respuesta, "output_text", None)
    if isinstance(texto, str) and texto.strip():
        return texto.strip()

    fragmentos: list[str] = []
    for elemento in getattr(respuesta, "output", []) or []:
        if getattr(elemento, "type", None) != "message":
            continue
        for parte in getattr(elemento, "content", []) or []:
            if getattr(parte, "type", None) == "output_text":
                fragmentos.append(getattr(parte, "text", ""))

    return "\n".join(f for f in fragmentos if f).strip()


class AgenteSoporte:
    """Agente de atención al cliente de NovaFibra."""

    def __init__(
        self,
        cliente: ClienteOpenAI | None = None,
        modelo: str | None = None,
        base: BaseConocimiento | None = None,
    ) -> None:
        self.base = base or cargar_base_conocimiento()
        self.modelo = modelo or os.getenv("OPENAI_MODEL", MODELO_POR_DEFECTO)
        self.prompt_sistema = construir_prompt_sistema(self.base)
        self._cliente = cliente or crear_cliente_openai()

    def _construir_entrada(
        self, historial: list[Turno], mensaje: str, datos: str
    ) -> list[dict[str, str]]:
        """Arma el arreglo `input` de la Responses API con el historial reciente."""
        recientes = historial[-TURNOS_DE_CONTEXTO:]
        entrada = [{"role": t.rol, "content": t.contenido} for t in recientes]
        entrada.append({"role": "user", "content": mensaje + datos})
        return entrada

    def _llamar_modelo(self, entrada: list[dict[str, str]]) -> str:
        try:
            respuesta = self._cliente.responses.create(
                model=self.modelo,
                instructions=self.prompt_sistema,
                input=entrada,
                max_output_tokens=MAX_TOKENS_RESPUESTA,
            )
        except Exception as exc:
            raise ErrorOpenAI(f"La llamada a la API de OpenAI falló: {exc}") from exc

        texto = extraer_texto(respuesta)
        if not texto:
            raise ErrorOpenAI("La API devolvió una respuesta vacía.")
        return texto

    def responder(
        self, mensaje: str, historial: list[Turno] | None = None, id_sesion: str = "anonimo"
    ) -> RespuestaAgente:
        """
        Resuelve un turno de conversación.

        Secuencia: reglas de escalamiento → acciones simuladas → llamada al
        modelo → detección del marcador de escalamiento.
        """
        mensaje = mensaje.strip()
        if not mensaje:
            raise ValueError("El mensaje del cliente no puede estar vacío.")

        historial = historial or []

        # 1. Capa determinista: hay casos que nunca debe resolver el bot.
        veredicto = evaluar_mensaje(mensaje)

        # 2. Consultas a sistemas internos simulados.
        acciones = detectar_acciones(mensaje, id_sesion)
        datos = formatear_datos_consultados([a.resultado for a in acciones])

        # 3. Turno del modelo.
        entrada = self._construir_entrada(historial, mensaje, datos)
        texto = self._llamar_modelo(entrada)

        # 4. El modelo puede pedir el escalamiento por su cuenta.
        pidio_escalar = respuesta_contiene_marcador(texto)
        texto = limpiar_marcador(texto)

        ticket: Ticket | None = None
        if veredicto.escalar or pidio_escalar:
            motivo = veredicto.motivo or "Consulta fuera del alcance del asistente virtual"
            ticket = crear_ticket(motivo=motivo, resumen=mensaje)
            texto = f"{texto}\n\n{MENSAJE_ESCALAMIENTO}".strip()

        return RespuestaAgente(texto=texto, acciones=acciones, ticket=ticket)
