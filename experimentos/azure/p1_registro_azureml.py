"""Prueba 1: el registro de modelos del proyecto sobre Azure Machine Learning (MLflow).

Ejecuta el flujo real del Supervisor con datos sintéticos (no usa datos de la compañía):
entrenamiento → candidato → promoción a vigente → inferencia con el vigente.
Verifica si el registro de MLflow de Azure ML acepta los alias "candidato" y "vigente".

Uso:
    python -m experimentos.azure.p1_registro_azureml                       # usa MLFLOW_TRACKING_URI
    python -m experimentos.azure.p1_registro_azureml --tracking-uri sqlite:///p1.db   # prueba local
"""
import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from agentes.supervisor import Supervisor
from contratos.base import TipoFlujo
from contratos.supervisor import SupervisorInput
from core.registro_modelos import RegistroModelos

DATOS_SINTETICOS = [
    {"temp_refrigerante": 120.0, "presion_carter": 30.0, "fe_ppm": 80.0, "cu_ppm": 20.0, "pqi": 150.0},
    {"temp_refrigerante": 95.0, "presion_carter": 40.0, "fe_ppm": 50.0, "cu_ppm": 10.0, "pqi": 90.0},
]
RESULTADOS = Path(__file__).parent / "resultados"
COMPONENTES = Path(__file__).resolve().parents[2] / "components"


def _solicitud(tipo: TipoFlujo, rid: str) -> SupervisorInput:
    return SupervisorInput(request_id=rid, caso_uso_id="p1-azureml", equipo="SINTETICO",
                           tipo_flujo=tipo, fecha_corte=date(2026, 1, 31),
                           ruta_componentes=str(COMPONENTES))


def ejecutar(tracking_uri: str) -> dict:
    """Corre los pasos y devuelve qué funcionó; no se detiene en el primer error."""
    pasos = {}
    registro = RegistroModelos(tracking_uri)
    sup = Supervisor(registro=registro)
    sello = datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        est = sup.ejecutar_solicitud(_solicitud(TipoFlujo.ENTRENAMIENTO, f"p1-ent-{sello}"),
                                     DATOS_SINTETICOS)
        reg = est.salidas.get("registro_modelo")
        pasos["entrenamiento_y_candidato"] = {"ok": bool(reg), "detalle": reg or est.errores}
        if not reg:
            return pasos
    except Exception as e:  # noqa: BLE001 - se reporta, no se oculta
        pasos["entrenamiento_y_candidato"] = {"ok": False, "detalle": repr(e)}
        return pasos
    try:
        registro.promover("motor_diesel", reg["version"])
        vigente = registro.cargar("motor_diesel")
        pasos["alias_vigente"] = {"ok": vigente is not None and vigente.version_modelo == reg["version"],
                                  "detalle": vigente.model_dump() if vigente else None}
    except Exception as e:  # noqa: BLE001
        pasos["alias_vigente"] = {"ok": False, "detalle": repr(e)}
    try:
        inf = sup.ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA, f"p1-inf-{sello}"),
                                     DATOS_SINTETICOS)
        pasos["inferencia_con_vigente"] = {"ok": "inferencia" in inf.salidas,
                                           "detalle": inf.errores or inf.fase.value}
    except Exception as e:  # noqa: BLE001
        pasos["inferencia_con_vigente"] = {"ok": False, "detalle": repr(e)}
    return pasos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tracking-uri", default=os.environ.get("MLFLOW_TRACKING_URI"))
    args = ap.parse_args(argv)
    if not args.tracking_uri:
        print("Falta MLFLOW_TRACKING_URI (o --tracking-uri). Ver experimentos/azure/README.md")
        return 2
    pasos = ejecutar(args.tracking_uri)
    destino = "azureml" if args.tracking_uri.startswith("azureml") else args.tracking_uri.split(":")[0]
    RESULTADOS.mkdir(exist_ok=True)
    salida = RESULTADOS / f"p1_registro_{destino}.json"
    salida.write_text(json.dumps({"destino": destino, "pasos": pasos}, indent=2,
                                 ensure_ascii=False, default=str), encoding="utf-8")
    for nombre, p in pasos.items():
        print(f"{'OK ' if p['ok'] else 'FALLA'}  {nombre}: {p['detalle'] if not p['ok'] else ''}")
    print(f"Resultado guardado en {salida}")
    return 0 if all(p["ok"] for p in pasos.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
