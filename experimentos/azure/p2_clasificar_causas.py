"""Prueba 2: ¿un LLM clasifica bien las fallas de motor según el FMEA?

Toma los 14 cambios de motor de docs/fase0/eventos_motor_dmh_798_borrador.csv y le pide a un
agente de Microsoft Agent Framework (modelo del proyecto de Foundry, p. ej. gpt-5) el grupo de falla
y los modos FMEA compatibles, con salida estructurada. Luego compara contra la propuesta manual.

- La propuesta manual NO se le muestra al modelo (clasificación a ciegas).
- Por defecto solo se envía texto técnico: sin equipo, serie ni fechas.
- Cada evento se clasifica N veces para medir consistencia.

Uso:
    python -m experimentos.azure.p2_clasificar_causas --repeticiones 3
Configuración: la misma del laboratorio (.env con AZURE_AI_PROJECT_ENDPOINT y
AZURE_AI_MODEL_DEPLOYMENT_NAME, y `az login`).
"""
import argparse
import asyncio
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel, Field

RAIZ = Path(__file__).resolve().parents[2]
EVENTOS = RAIZ / "docs/fase0/eventos_motor_dmh_798_borrador.csv"
FMEA = RAIZ / "components/motor_diesel/fmea.json"
RESULTADOS = Path(__file__).parent / "resultados"

GRUPOS = Literal[
    "distribucion_delantera", "distribucion_tren_valvulas", "bloqueo_hidraulico_ingreso_fluido",
    "lubricacion_cojinetes", "lubricacion_sin_causa", "falla_con_pcr_cumplido", "pcr",
    "otro", "indeterminado",
]
CAMPOS_TECNICOS = ["tipo_cambio", "horas_motor_removido_h", "descripcion_falla",
                   "descripcion_falla_base", "modo_falla_estandarizado", "causa_raiz_resumen",
                   "pieza_fallada", "causa_raiz"]


def es_limite_de_tasa(e: Exception) -> bool:
    """429 del despliegue: se superó el límite de tokens o solicitudes por minuto."""
    texto = repr(e)
    return "429" in texto or "rate_limit" in texto


async def con_reintentos(llamada, intentos: int = 4, espera_s: int = 65):
    """Ejecuta la llamada asíncrona; ante un 429 espera a que se reinicie la cuota por minuto."""
    for i in range(1, intentos + 1):
        try:
            return await llamada()
        except Exception as e:  # noqa: BLE001 - solo se reintenta el 429
            if not es_limite_de_tasa(e) or i == intentos:
                raise
            print(f"  límite de tokens por minuto alcanzado; espero {espera_s} s (intento {i}/{intentos})")
            await asyncio.sleep(espera_s)


class Clasificacion(BaseModel):
    grupo_falla: GRUPOS
    modos_fmea: List[str] = Field(description="IDs MFP-xx compatibles; vacío si ninguno aplica")
    requiere_modo_nuevo: bool = Field(description="true si la falla no está cubierta por el FMEA")
    confianza: Literal["alta", "media", "baja"]
    evidencia: List[str] = Field(description="frases textuales del registro que sustentan la clasificación")
    justificacion: str


def prompt_sistema() -> str:
    modos = json.loads(FMEA.read_text(encoding="utf-8"))["modos_falla"]
    resumen = [{"id": m["id"], "nombre": m["nombre"], "precursores": m["precursores"]} for m in modos]
    return (
        "Eres un ingeniero de confiabilidad de motores diésel de camiones mineros CAT 798AC.\n"
        "Clasifica un cambio de motor a partir de su registro técnico.\n"
        "Reglas:\n"
        "- 'baja presión aceite motor' suele ser el síntoma con que se detuvo el equipo, no la causa.\n"
        "- Un cambio programado por PCR es fin de vida, no falla (grupo 'pcr'). Si tenía el PCR\n"
        "  cumplido pero falló antes de su cambio programado, usa 'falla_con_pcr_cumplido'.\n"
        "- Usa solo la información del registro; si no alcanza, confianza baja o 'indeterminado'.\n"
        "- La evidencia debe ser texto copiado del registro, no inventado.\n"
        "- Compatibilidad con el FMEA, no diagnóstico.\n"
        f"Modos FMEA vigentes: {json.dumps(resumen, ensure_ascii=False)}"
    )


def registro_tecnico(fila: dict) -> str:
    return "\n".join(f"{c}: {fila.get(c, '')}" for c in CAMPOS_TECNICOS if fila.get(c, "").strip())


def opciones_modelo(esfuerzo: str = "low", max_tokens: int = 4000) -> dict:
    """Razonamiento bajo y respuesta acotada: Azure descuenta max_tokens del límite por minuto."""
    return {"max_tokens": max_tokens, "reasoning": {"effort": esfuerzo}}


def cliente_foundry(modelo: str):
    from agent_framework.foundry import FoundryChatClient  # import diferido: solo en la VM
    from azure.identity import AzureCliCredential

    return FoundryChatClient(credential=AzureCliCredential(),
                             project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], model=modelo)


def agente_foundry(modelo: str, opciones: dict):
    """Agente de Agent Framework sobre el proyecto de Foundry, igual que en el laboratorio."""
    return cliente_foundry(modelo).as_agent(name="clasificador_fallas", instructions=prompt_sistema(),
                                            default_options=opciones)


async def clasificar(agente, fila: dict) -> Clasificacion:
    resp = await con_reintentos(lambda: agente.run(registro_tecnico(fila),
                                                   options={"response_format": Clasificacion}))
    return resp.value if isinstance(resp.value, Clasificacion) else Clasificacion.model_validate_json(resp.text)


async def evaluar(agente, repeticiones: int, pausa_s: float = 0) -> List[dict]:
    with EVENTOS.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    salida = []
    for fila in filas:
        corridas = []
        for _ in range(repeticiones):
            try:
                corridas.append(await clasificar(agente, fila))
                await asyncio.sleep(pausa_s)
            except Exception as e:  # noqa: BLE001 - se registra y se sigue con el resto
                print(f"error en {fila['equipo_id']} {fila['fecha_retiro']}: {e!r}")
        grupos = Counter(c.grupo_falla for c in corridas)
        grupo, votos = grupos.most_common(1)[0] if grupos else ("sin_respuesta", 0)
        principal = next((c for c in corridas if c.grupo_falla == grupo), None)
        salida.append({
            "equipo_id": fila["equipo_id"], "fecha_retiro": fila["fecha_retiro"],
            "grupo_manual": fila["grupo_falla_propuesto"], "grupo_llm": grupo,
            "coincide_grupo": grupo == fila["grupo_falla_propuesto"],
            "consistencia": f"{votos}/{len(corridas)}",
            "modo_manual": fila["modo_fmea_propuesto"],
            "modos_llm": ";".join(principal.modos_fmea) if principal else "",
            "requiere_modo_nuevo": principal.requiere_modo_nuevo if principal else "",
            "confianza": principal.confianza if principal else "",
            "evidencia": " | ".join(principal.evidencia) if principal else "",
            "justificacion": principal.justificacion if principal else "",
        })
    return salida


def resumen(filas: List[dict], modelo: str, repeticiones: int) -> str:
    n = len(filas)
    ok = sum(f["coincide_grupo"] for f in filas)
    estables = sum(f["consistencia"].split("/")[0] == f["consistencia"].split("/")[1] for f in filas)
    lineas = [f"# Prueba 2: clasificación de causas con {modelo}", "",
              f"- Eventos: {n} · repeticiones por evento: {repeticiones}",
              f"- Coincide con la propuesta manual (grupo): {ok}/{n}",
              f"- Clasificación estable en todas las repeticiones: {estables}/{n}", "",
              "| Equipo | Fecha | Manual | LLM | Consistencia | Modos LLM | Confianza |",
              "|---|---|---|---|---|---|---|"]
    lineas += [f"| {f['equipo_id']} | {f['fecha_retiro']} | {f['grupo_manual']} | {f['grupo_llm']}"
               f"{'' if f['coincide_grupo'] else ' ⚠️'} | {f['consistencia']} | {f['modos_llm']} | "
               f"{f['confianza']} |" for f in filas]
    lineas += ["", "Las diferencias (⚠️) se revisan con Confiabilidad: pueden ser errores del modelo "
               "o de la propuesta manual."]
    return "\n".join(lineas) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--pausa", type=float, default=5, help="segundos entre llamadas (cuotas bajas)")
    ap.add_argument("--esfuerzo", default="low", choices=["minimal", "low", "medium", "high"],
                    help="esfuerzo de razonamiento (gpt-5); más bajo = menos tokens")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--modelo", default=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5"))
    args = ap.parse_args(argv)
    filas = asyncio.run(evaluar(agente_foundry(args.modelo, opciones_modelo(args.esfuerzo, args.max_tokens)),
                               args.repeticiones, args.pausa))
    RESULTADOS.mkdir(exist_ok=True)
    with (RESULTADOS / f"p2_clasificacion_{args.modelo}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    texto = resumen(filas, args.modelo, args.repeticiones)
    (RESULTADOS / f"p2_resumen_{args.modelo}.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    sys.exit(main())
