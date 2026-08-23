"""
Carga de la base de conocimiento de NovaFibra.

La base vive en `data/knowledge_base.json` y contiene información ficticia de
la empresa. El chatbot la recibe como contexto para que sus respuestas se
apoyen en datos concretos en lugar de en lo que el modelo haya memorizado.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUTA_BASE = Path(__file__).resolve().parent.parent
RUTA_KB = RUTA_BASE / "data" / "knowledge_base.json"

CLAVES_REQUERIDAS = {
    "empresa",
    "horarios",
    "servicios",
    "cargos_adicionales",
    "politicas",
    "preguntas_frecuentes",
    "criterios_escalamiento",
}


class ErrorBaseConocimiento(Exception):
    """La base de conocimiento no existe o no tiene la forma esperada."""


@dataclass(frozen=True)
class BaseConocimiento:
    """Vista de solo lectura sobre el JSON de la empresa."""

    datos: dict[str, Any]

    @property
    def nombre_empresa(self) -> str:
        return self.datos["empresa"]["nombre"]

    @property
    def servicios(self) -> list[dict[str, Any]]:
        return self.datos["servicios"]

    @property
    def politicas(self) -> list[dict[str, Any]]:
        return self.datos["politicas"]

    @property
    def preguntas_frecuentes(self) -> list[dict[str, Any]]:
        return self.datos["preguntas_frecuentes"]

    @property
    def criterios_escalamiento(self) -> list[str]:
        return self.datos["criterios_escalamiento"]

    def buscar_servicio(self, texto: str) -> dict[str, Any] | None:
        """Devuelve el servicio cuyo nombre aparezca en el texto, si lo hay."""
        texto_normalizado = texto.lower()
        for servicio in self.servicios:
            if servicio["nombre"].lower() in texto_normalizado:
                return servicio
        return None

    def como_texto(self) -> str:
        """
        Serializa la base a texto plano para insertarla en el prompt.

        Se usa una redacción explícita en lugar de volcar el JSON crudo: los
        modelos siguen mejor las instrucciones cuando el contexto está escrito
        en prosa estructurada, y así se evita que confundan claves internas
        (`id`, `null`) con información de cara al cliente.
        """
        d = self.datos
        empresa = d["empresa"]
        partes: list[str] = []

        partes.append(
            f"EMPRESA: {empresa['nombre']} — {empresa['sector']}.\n"
            f"Cobertura: {empresa['cobertura']}.\n"
            f"Teléfono: {empresa['telefono']} · Correo: {empresa['correo_soporte']} · "
            f"Web: {empresa['sitio_web']}"
        )

        horarios = "\n".join(f"- {k.replace('_', ' ').capitalize()}: {v}" for k, v in d["horarios"].items())
        partes.append(f"HORARIOS DE ATENCIÓN:\n{horarios}")

        lineas_servicios = []
        for s in d["servicios"]:
            velocidad = f" · {s['velocidad']}" if s.get("velocidad") else ""
            incluye = "; ".join(s["incluye"])
            lineas_servicios.append(
                f"- {s['nombre']} ({s['categoria']}): {s['precio_mensual_mxn']} MXN/mes{velocidad}.\n"
                f"  Incluye: {incluye}.\n"
                f"  Recomendado para: {s['ideal_para']}."
            )
        partes.append("SERVICIOS Y PRECIOS:\n" + "\n".join(lineas_servicios))

        cargos = "\n".join(
            f"- {c['concepto']}: {c['monto_mxn']} MXN. {c['nota']}" for c in d["cargos_adicionales"]
        )
        partes.append(f"CARGOS ADICIONALES:\n{cargos}")

        politicas = "\n".join(f"- {p['titulo']}: {p['detalle']}" for p in d["politicas"])
        partes.append(f"POLÍTICAS:\n{politicas}")

        faqs = "\n".join(
            f"- P: {f['pregunta']}\n  R: {f['respuesta']}" for f in d["preguntas_frecuentes"]
        )
        partes.append(f"PREGUNTAS FRECUENTES:\n{faqs}")

        criterios = "\n".join(f"- {c}" for c in d["criterios_escalamiento"])
        partes.append(f"CRITERIOS DE ESCALAMIENTO A UN AGENTE HUMANO:\n{criterios}")

        return "\n\n".join(partes)


def cargar_base_conocimiento(ruta: Path | str | None = None) -> BaseConocimiento:
    """Lee y valida el JSON de la base de conocimiento."""
    destino = Path(ruta) if ruta is not None else RUTA_KB

    if not destino.exists():
        raise ErrorBaseConocimiento(
            f"No se encontró la base de conocimiento en {destino}. "
            "Verifica que el archivo data/knowledge_base.json exista."
        )

    try:
        with destino.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ErrorBaseConocimiento(
            f"La base de conocimiento no es un JSON válido ({destino}): {exc}"
        ) from exc

    faltantes = CLAVES_REQUERIDAS - set(datos)
    if faltantes:
        raise ErrorBaseConocimiento(
            f"A la base de conocimiento le faltan las claves: {', '.join(sorted(faltantes))}"
        )

    return BaseConocimiento(datos=datos)
