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
import difflib
import json
import os
import sys
from typing import cast

from experimentos.azure.p2_clasificar_causas import (EVENTOS, FMEA, RESULTADOS, Consumo, cliente_foundry,
                                                    con_reintentos, opciones_modelo, registro_tecnico)

# Ajustadas tras las corridas de los casos 0, 3 y 4 (ver resultados/conclusiones_p3.md):
# el síntoma no es el modo, y el revisor conoce qué cubre cada fuente y desde cuándo.
INSTRUCCIONES = {
    "evidencia": (
        "Eres analista de evidencia de fallas de motores diésel CAT 798AC. Del registro recibido, lista en "
        "viñetas solo los hechos explícitos: síntoma de detención, pieza fallada, causa raíz declarada y "
        "condición del componente. Cita el texto. Si un dato no está, escribe 'no informado'. No interpretes."),
    "fmea": (
        "Eres especialista en FMEA de motores. Con los hechos del agente de evidencia, indica qué modos del "
        "FMEA son compatibles (id y por qué) o si la falla no está cubierta y requiere un modo nuevo. "
        "El síntoma de detención (por ejemplo, baja presión de aceite) no es el modo de falla: asigna los "
        "modos por la causa y la pieza fallada, y menciona el síntoma solo como consecuencia. "
        "Es compatibilidad, no diagnóstico. Modos FMEA vigentes: {modos}"),
    "revisor": (
        "Eres ingeniero de Confiabilidad y revisas el análisis anterior. En máximo 5 viñetas: qué conclusión "
        "está bien sustentada, qué es suposición, y qué verificar antes de aceptarla, indicando la fuente. "
        "Fuentes disponibles y lo que cubren: análisis de aceite SOS (elementos, viscosidad, Na/K, hollín; "
        "historia desde 2022); eventos y tendencias VIMS (alarmas, presión de aceite, temperaturas, "
        "diferencial de filtros); rellenos de aceite y refrigerante; particulado de rutina (test de parche, "
        "rejillas, tapones magnéticos), en Argos hasta mayo de 2026 y en Cat Inspect desde junio de 2026, "
        "que no registran desarmes; el informe de falla AFA/RCA y el informe de taller, únicas fuentes de "
        "hallazgos de desarme. Usa solo esas fuentes."),
}


NO_REPETIR = (" Responde solo con tu propio análisis, en tu rol; no copies ni repitas el mensaje del "
              "agente anterior.")
UMBRAL_ECO = 0.7  # similitud de texto sobre la que una respuesta se considera copia de la anterior


def instrucciones() -> dict:
    modos = json.loads(FMEA.read_text(encoding="utf-8"))["modos_falla"]
    resumen = [{"id": m["id"], "nombre": m["nombre"]} for m in modos]
    return {k: (v.format(modos=json.dumps(resumen, ensure_ascii=False)) if k == "fmea" else v)
            + (NO_REPETIR if k != "evidencia" else "")
            for k, v in INSTRUCCIONES.items()}


def detectar_eco(mensajes: list) -> list:
    """Agentes cuya respuesta es casi igual a la del agente anterior (se copió en vez de analizar)."""
    agentes = [(a, t) for a, t in mensajes if a in INSTRUCCIONES]
    return [actual[0] for previo, actual in zip(agentes, agentes[1:])
            if difflib.SequenceMatcher(None, previo[1].strip(), actual[1].strip()).ratio() >= UMBRAL_ECO]


def leer_caso(indice: int) -> dict:
    with EVENTOS.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))[indice]


async def analizar(texto_caso: str, modelo: str, opciones: dict, intentos: int = 3,
                   consumo: Consumo = None) -> tuple:
    """Corre el flujo; si un agente copia al anterior, lo repite (hasta `intentos` veces).
    El consumo suma todas las corridas, también las repetidas por eco."""
    for i in range(1, intentos + 1):
        mensajes = await _correr_flujo(texto_caso, modelo, opciones, consumo)
        eco = detectar_eco(mensajes)
        if not eco:
            return mensajes, [], i
        print(f"  eco detectado en {eco} (intento {i}/{intentos})")
    return mensajes, eco, intentos


async def _correr_flujo(texto_caso: str, modelo: str, opciones: dict, consumo: Consumo = None) -> list:
    from agent_framework import Message  # imports diferidos: solo en la VM
    from agent_framework.orchestrations import SequentialBuilder

    cliente = cliente_foundry(modelo)
    agentes = [cliente.as_agent(name=n, instructions=t, default_options=opciones)
               for n, t in instrucciones().items()]
    flujo = SequentialBuilder(participants=agentes, output_from="all").build()
    resultado = await con_reintentos(lambda: flujo.run(f"Registro del cambio de motor:\n{texto_caso}"))
    salida = []
    for respuesta in resultado.get_outputs():
        if consumo is not None:
            consumo.sumar(getattr(respuesta, "usage_details", None))
        for msg in cast(list[Message], respuesta.messages):
            salida.append((msg.author_name or msg.role, msg.text))
    return salida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--caso", type=int, default=4, help="fila del listado de eventos (0 a 13)")
    ap.add_argument("--esfuerzo", default="medium", choices=["minimal", "low", "medium", "high"],
                    help="esfuerzo de razonamiento (gpt-5); low ahorra tokens si la cuota es baja")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--modelo", default=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5"))
    args = ap.parse_args(argv)
    fila = leer_caso(args.caso)
    texto = registro_tecnico(fila)
    opciones = opciones_modelo(args.esfuerzo, args.max_tokens)
    consumo = Consumo()
    mensajes, eco, intentos = asyncio.run(analizar(texto, args.modelo, opciones, consumo=consumo))
    md = [f"# Prueba 3: análisis secuencial del caso {args.caso} ({args.modelo})", "",
          f"Razonamiento: {args.esfuerzo} · máximo de tokens: {args.max_tokens} · corridas: {intentos}", "",
          f"Consumo: {consumo.texto()}", ""]
    if eco:
        md += [f"> ⚠️ Eco sin resolver: {', '.join(eco)} repitió al agente anterior en todos los intentos.", ""]
    md += ["## Registro enviado", "", "```", texto, "```", ""]
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
