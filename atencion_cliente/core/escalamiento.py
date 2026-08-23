"""
Detección de escalamiento y generación de tickets de soporte.

El escalamiento se decide en dos capas complementarias:

1. **Previa y determinista** — se inspecciona el mensaje del cliente antes de
   llamar al modelo. Cubre los casos que nunca deben quedar en manos del bot
   (asuntos legales, fraude, datos bancarios, petición explícita de una
   persona). No depende del criterio del modelo, así que no puede fallar por
   una respuesta poco afortunada.

2. **Del modelo** — el prompt de sistema instruye al modelo para que emita el
   marcador `[ESCALAR]` cuando no pueda resolver el caso. Cubre lo que la
   heurística no anticipa, sobre todo la falta de información en la base de
   conocimiento.

Los tickets son simulados: se generan en memoria con un folio reproducible.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .prompts import MARCADOR_ESCALAMIENTO

# (motivo legible, patrón). El motivo se registra en el ticket.
_REGLAS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "Asunto legal o regulatorio",
        re.compile(r"\b(demanda|demandar|abogad\w+|profeco|legal|juicio|denuncia\w*|ift)\b", re.I),
    ),
    (
        "Posible fraude o cargo no reconocido",
        re.compile(r"\b(fraude|estafa|clonaron|no reconozco (este|ese|el) cargo|cargo no autorizado)\b", re.I),
    ),
    (
        "Solicitud sobre datos bancarios o personales sensibles",
        re.compile(r"\b(tarjeta de cr[ée]dito|n[uú]mero de tarjeta|cvv|clabe|contrase[ñn]a de mi cuenta|datos bancarios)\b", re.I),
    ),
    (
        "El cliente solicita hablar con una persona",
        re.compile(r"\b(hablar con (un|una) (persona|humano|agente|ejecutivo)|agente humano|operador real|quiero un humano)\b", re.I),
    ),
    (
        "Cancelación con inconformidad o reclamación de penalización",
        re.compile(r"\b(cancelar).{0,40}\b(penalizaci[oó]n|injust\w+|no acepto|me niego)\b", re.I),
    ),
    (
        "Reclamación de reembolso de importe elevado",
        re.compile(r"\breembols\w+\b(?=.*\b([2-9]\d{3,}|\d{5,})\b)", re.I),
    ),
)


@dataclass(frozen=True)
class Ticket:
    """Ticket de soporte simulado."""

    folio: str
    motivo: str
    resumen: str
    prioridad: str
    creado_en: datetime
    respuesta_estimada: datetime

    def como_texto(self) -> str:
        return (
            f"Ticket {self.folio} · Prioridad {self.prioridad}\n"
            f"Motivo: {self.motivo}\n"
            f"Respuesta estimada antes del "
            f"{self.respuesta_estimada.strftime('%d/%m/%Y a las %H:%M')}"
        )


@dataclass
class ResultadoEscalamiento:
    """Veredicto de la capa determinista."""

    escalar: bool
    motivo: str = ""
    reglas_activadas: list[str] = field(default_factory=list)


def evaluar_mensaje(mensaje: str) -> ResultadoEscalamiento:
    """Aplica las reglas deterministas sobre el mensaje del cliente."""
    activadas = [motivo for motivo, patron in _REGLAS if patron.search(mensaje)]

    if not activadas:
        return ResultadoEscalamiento(escalar=False)

    return ResultadoEscalamiento(
        escalar=True,
        motivo=activadas[0],
        reglas_activadas=activadas,
    )


def respuesta_contiene_marcador(respuesta: str) -> bool:
    """Indica si el modelo pidió escalar el caso."""
    return MARCADOR_ESCALAMIENTO in respuesta


def limpiar_marcador(respuesta: str) -> str:
    """Retira el marcador interno antes de mostrar la respuesta al cliente."""
    sin_marcador = respuesta.replace(MARCADOR_ESCALAMIENTO, "")
    # Deja como mucho una línea en blanco consecutiva.
    return re.sub(r"\n{3,}", "\n\n", sin_marcador).strip()


def _prioridad(motivo: str) -> str:
    altos = ("legal", "fraude", "bancarios")
    return "Alta" if any(p in motivo.lower() for p in altos) else "Media"


def crear_ticket(motivo: str, resumen: str, ahora: datetime | None = None) -> Ticket:
    """
    Genera un ticket de soporte simulado.

    El folio se deriva del contenido para que sea reproducible en las pruebas;
    en un sistema real lo asignaría la plataforma de tickets.
    """
    momento = ahora or datetime.now()
    huella = hashlib.sha256(f"{motivo}|{resumen}|{momento.date()}".encode("utf-8")).hexdigest()
    folio = f"SOP-{huella[:6].upper()}"
    prioridad = _prioridad(motivo)
    horas = 4 if prioridad == "Alta" else 24

    return Ticket(
        folio=folio,
        motivo=motivo,
        resumen=resumen.strip()[:280],
        prioridad=prioridad,
        creado_en=momento,
        respuesta_estimada=momento + timedelta(hours=horas),
    )


MENSAJE_ESCALAMIENTO = (
    "Esta consulta requiere la intervención de un agente humano. "
    "Se ha generado un ticket de soporte y un especialista te contactará."
)
