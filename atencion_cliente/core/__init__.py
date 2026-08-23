"""Núcleo del asistente de atención al cliente de NovaFibra."""

from .chatbot import (
    AgenteSoporte,
    ErrorConfiguracion,
    ErrorOpenAI,
    RespuestaAgente,
    Turno,
    crear_cliente_openai,
)
from .escalamiento import Ticket
from .knowledge_base import ErrorBaseConocimiento, cargar_base_conocimiento

__all__ = [
    "AgenteSoporte",
    "ErrorConfiguracion",
    "ErrorOpenAI",
    "ErrorBaseConocimiento",
    "RespuestaAgente",
    "Ticket",
    "Turno",
    "cargar_base_conocimiento",
    "crear_cliente_openai",
]
