"""
Simulación de los sistemas internos de NovaFibra.

En un despliegue real estas funciones consultarían el CRM, el sistema de
facturación o la plataforma de monitoreo de red. Aquí devuelven datos
inventados de forma **determinista**: el mismo folio produce siempre el mismo
resultado, de modo que una conversación de varios turnos se mantenga coherente.

El resultado de cada acción se inyecta en el mensaje que recibe el modelo bajo
el encabezado DATOS CONSULTADOS (ver `prompts.py`).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Palabras que disparan cada consulta simulada.
_PALABRAS_PEDIDO = (
    "pedido", "orden", "instalacion", "instalación", "contratacion",
    "contratación", "equipo", "router", "envio", "envío", "folio",
)
_PALABRAS_CUENTA = (
    "saldo", "recibo", "factura", "facturacion", "facturación", "pago",
    "adeudo", "cobro", "cargo", "cuenta",
)
_PALABRAS_FALLA = (
    "lento", "lenta", "sin internet", "no funciona", "no sirve", "se cae",
    "intermitente", "falla", "cortes", "desconecta", "no navega", "caida",
    "caída",
)

_PATRON_FOLIO = re.compile(r"\b(?:NF[-\s]?)?(\d{5,8})\b", re.IGNORECASE)

_ESTADOS_PEDIDO = (
    "En preparación en almacén",
    "Asignado a cuadrilla de instalación",
    "En ruta, la cuadrilla llega hoy",
    "Instalación completada y servicio activo",
    "Reprogramado a petición del cliente",
)


@dataclass(frozen=True)
class AccionSimulada:
    """Una consulta a un sistema interno simulado."""

    etiqueta: str
    resultado: str


def _semilla(valor: str) -> int:
    """Entero estable derivado de un texto, para generar datos reproducibles."""
    return int(hashlib.sha256(valor.encode("utf-8")).hexdigest()[:8], 16)


def _extraer_folio(texto: str) -> str | None:
    coincidencia = _PATRON_FOLIO.search(texto)
    return coincidencia.group(1) if coincidencia else None


def _contiene(texto: str, palabras: tuple[str, ...]) -> bool:
    return any(p in texto for p in palabras)


def consultar_pedido(folio: str) -> AccionSimulada:
    """Devuelve el estado simulado de un pedido o instalación."""
    s = _semilla(f"pedido:{folio}")
    estado = _ESTADOS_PEDIDO[s % len(_ESTADOS_PEDIDO)]
    dias = s % 5 + 1
    return AccionSimulada(
        etiqueta=f"Consultando estado del pedido NF-{folio}...",
        resultado=(
            f"Pedido NF-{folio}: {estado}. "
            f"Fecha estimada de finalización: dentro de {dias} día(s) hábil(es)."
        ),
    )


def consultar_cuenta(identificador: str) -> AccionSimulada:
    """Devuelve el estado de cuenta simulado de un cliente."""
    s = _semilla(f"cuenta:{identificador}")
    saldo = (s % 1200) - 200  # puede resultar negativo: saldo a favor
    dia_corte = 25
    if saldo > 0:
        detalle = f"saldo pendiente de {saldo} MXN con vencimiento el día {dia_corte + 10} del mes"
    elif saldo < 0:
        detalle = f"saldo a favor de {abs(saldo)} MXN aplicable al siguiente recibo"
    else:
        detalle = "sin adeudos"
    return AccionSimulada(
        etiqueta="Consultando base de datos de clientes...",
        resultado=(
            f"Cuenta {identificador}: {detalle}. "
            f"Último pago registrado hace {s % 28 + 1} día(s). Servicio activo."
        ),
    )


def diagnosticar_linea(identificador: str) -> AccionSimulada:
    """Devuelve un diagnóstico simulado del enlace del cliente."""
    s = _semilla(f"linea:{identificador}")
    potencia = -(15 + s % 10)
    latencia = 4 + s % 25
    perdida = s % 4
    incidencia = (s % 3 == 0)

    if incidencia:
        veredicto = (
            "Se detecta una incidencia activa en el nodo que da servicio a la zona. "
            "Tiempo estimado de restablecimiento: 3 horas."
        )
    elif perdida >= 2 or potencia <= -22:
        veredicto = (
            "El enlace presenta degradación en el tramo de fibra del domicilio. "
            "Procede generar un reporte técnico con visita."
        )
    else:
        veredicto = (
            "El enlace opera dentro de parámetros normales; la lentitud probablemente "
            "provenga de la red Wi-Fi interna o de la saturación de dispositivos."
        )

    return AccionSimulada(
        etiqueta="Ejecutando diagnóstico remoto de la línea...",
        resultado=(
            f"Diagnóstico de línea: potencia óptica {potencia} dBm, "
            f"latencia {latencia} ms, pérdida de paquetes {perdida} %. {veredicto}"
        ),
    )


def detectar_acciones(mensaje: str, id_sesion: str) -> list[AccionSimulada]:
    """
    Decide qué consultas internas corresponden al mensaje del cliente.

    `id_sesion` se usa como identificador de cliente cuando el mensaje no
    incluye un folio explícito, de forma que los datos simulados sean
    consistentes durante toda la conversación.
    """
    texto = mensaje.lower()
    acciones: list[AccionSimulada] = []
    folio = _extraer_folio(mensaje)

    if folio and _contiene(texto, _PALABRAS_PEDIDO):
        acciones.append(consultar_pedido(folio))

    if _contiene(texto, _PALABRAS_CUENTA):
        acciones.append(consultar_cuenta(folio or id_sesion))

    if _contiene(texto, _PALABRAS_FALLA):
        acciones.append(diagnosticar_linea(folio or id_sesion))

    return acciones
