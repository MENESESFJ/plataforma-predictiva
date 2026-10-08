"""Carga del bundle de conocimiento de un componente (Knowledge as Code)."""
import json
from pathlib import Path

import yaml


def cargar_bundle(ruta: str, componente: str) -> dict:
    base = Path(ruta) / componente
    leer_json = lambda n: json.loads((base / n).read_text(encoding="utf-8"))
    return {
        "definition": leer_json("definition.json"),
        "quality_rules": yaml.safe_load((base / "quality_rules.yaml").read_text(encoding="utf-8")),
        "fmea": leer_json("fmea.json"),
        "action_catalog": leer_json("action_catalog.json"),
        "feature_catalog": leer_json("feature_catalog.json"),
    }
