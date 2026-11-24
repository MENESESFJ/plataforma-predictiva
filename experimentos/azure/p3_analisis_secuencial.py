"""Prueba 3: orquestación secuencial de agentes sobre un caso de motor (como el laboratorio 08).

Mismo patrón que el ejercicio de Microsoft Learn (SequentialBuilder), aplicado a un cambio de motor:
    evidencia → fmea → revisor
- evidencia: extrae del registro los hechos (síntoma, pieza, causa) sin inventar.
- fmea: propone modos FMEA compatibles o indica que falta un modo.
- revisor: rol de Confiabilidad; dice qué falta verificar y con qué datos (SOS, Cat Inspect, eventos).

Solo texto técnico del caso (sin equipo, serie ni fechas). Es una demo: la salida no es diagnóstico.

Uso:
    python -m experimentos.azure.p3_analisis_secuencial --caso 5
Configuración: .env del laboratorio (AZURE_AI_PROJECT_ENDPOINT, AZURE_AI_MODEL_DEPLOYMENT_NAME) y `az login`.
"""
import argparse
import asyncio
import csv
import json
import os
import sys
from typing import cast

from experimentos.azure.p2_clasificar_causas import (EVENTOS, FMEA, RESULTADOS, cliente_foundry,
                                                    con_reintentos, opciones_modelo, registro_tecnico)

INSTRUCCIONES = {
    "evidencia": (
        "Eres analista de evidencia de fallas de motores diésel CAT 798AC. Del registro recibido, lista en "
        "viñetas solo los hechos explícitos: síntoma de detención, pieza fallada, causa raíz declarada y "
        "condición del componente. Cita el texto. Si un dato no está, escribe 'no informado'. No interpretes."),
    "fmea": (
        "Eres especialista en FMEA de motores. Con los hechos del agente de evidencia, indica qué modos del "
        "FMEA son compatibles (id y por qué) o si la falla no está cubierta y requiere un modo nuevo. "
        "Es compatibilidad, no diagnóstico. Modos FMEA vigentes: {modos}"),
    "revisor": (
        "Eres ingeniero de Confiabilidad y revisas el análisis anterior. En máximo 5 viñetas: qué conclusión "
        "está bien sustentada, qué es suposición, y qué verificar antes de aceptarla, indicando la fuente "
        "(análisis de aceite SOS, inspección de particulado Cat Inspect, eventos VIMS, rellenos de aceite)."),
}


def instrucciones() -> dict:
    modos = json.loads(FMEA.read_text(encoding="utf-8"))["modos_falla"]
    resumen = [{"id": m["id"], "nombre": m["nombre"]} for m in modos]
    return {k: v.format(modos=json.dumps(resumen, ensure_ascii=False)) if k == "fmea" else v
            for k, v in INSTRUCCIONES.items()}


def leer_caso(indice: int) -> dict:
    with EVENTOS.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))[indice]


async def analizar(texto_caso: str, modelo: str, opciones: dict) -> list:
    from agent_framework import Message  # imports diferidos: solo en la VM
    from agent_framework.orchestrations import SequentialBuilder

    cliente = cliente_foundry(modelo)
    agentes = [cliente.as_agent(name=n, instructions=t, default_options=opciones)
               for n, t in instrucciones().items()]
    flujo = SequentialBuilder(participants=agentes, output_from="all").build()
    resultado = await con_reintentos(lambda: flujo.run(f"Registro del cambio de motor:\n{texto_caso}"))
    salida = []
    for respuesta in resultado.get_outputs():
        for msg in cast(list[Message], respuesta.messages):
            salida.append((msg.author_name or msg.role, msg.text))
    return salida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--caso", type=int, default=4, help="fila del listado de eventos (0 a 13)")
    ap.add_argument("--esfuerzo", default="low", choices=["minimal", "low", "medium", "high"],
                    help="esfuerzo de razonamiento (gpt-5); más bajo = menos tokens")
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--modelo", default=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5"))
    args = ap.parse_args(argv)
    fila = leer_caso(args.caso)
    texto = registro_tecnico(fila)
    mensajes = asyncio.run(analizar(texto, args.modelo, opciones_modelo(args.esfuerzo, args.max_tokens)))
    md = [f"# Prueba 3: análisis secuencial del caso {args.caso} ({args.modelo})", "",
          "## Registro enviado", "", "```", texto, "```", ""]
    for autor, contenido in mensajes:
        md += [f"## {autor}", "", contenido, ""]
    RESULTADOS.mkdir(exist_ok=True)
    destino = RESULTADOS / f"p3_caso_{args.caso}_{args.modelo}.md"
    destino.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"Resultado guardado en {destino}")
    return 0


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    sys.exit(main())
