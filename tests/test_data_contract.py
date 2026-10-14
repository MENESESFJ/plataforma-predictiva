"""El contrato del dataset debe cubrir todas las variables que usa el FMEA aprobado."""
import json
from pathlib import Path

import yaml

BASE = Path("components/motor_diesel")
CONTRATO = yaml.safe_load((BASE / "data_contract.yaml").read_text(encoding="utf-8"))


def test_contrato_cubre_variables_del_fmea():
    fmea = json.loads((BASE / "fmea.json").read_text(encoding="utf-8"))
    usadas = {v for m in fmea["modos_falla"] for v in m["variables"]}
    faltantes = usadas - set(CONTRATO["variables"])
    assert not faltantes, f"variables del FMEA sin definir en el contrato: {sorted(faltantes)}"


def test_variables_apuntan_a_fuentes_definidas():
    fuentes = set(CONTRATO["fuentes"])
    for grupo in ("variables", "contexto"):
        for nombre, v in CONTRATO[grupo].items():
            assert v["fuente"] in fuentes, f"{nombre}: fuente '{v['fuente']}' no definida"
            assert v.get("unidad"), f"{nombre}: falta unidad"


def test_cada_fuente_declara_regla_de_corte():
    for nombre, f in CONTRATO["fuentes"].items():
        assert f.get("fecha_disponible") and f.get("regla_corte"), f"{nombre}: sin regla point-in-time"


def test_fuentes_prohibidas_no_alimentan_variables():
    prohibidas = {n for n, f in CONTRATO["fuentes"].items() if f.get("prohibido_como_predictor")}
    assert "afa_rca" in prohibidas
    for grupo in ("variables", "contexto"):
        for nombre, v in CONTRATO[grupo].items():
            assert v["fuente"] not in prohibidas, f"{nombre} usa una fuente posterior al evento"


def test_fmea_no_declara_validado_sin_decision():
    fmea = json.loads((BASE / "fmea.json").read_text(encoding="utf-8"))
    decisiones = json.loads(Path("knowledge/fmea/revision/decisiones.json").read_text(encoding="utf-8"))
    niveles = set(decisiones["niveles_validacion"])
    ids = {d["id"] for d in decisiones["decisiones"]}
    for m in fmea["modos_falla"]:
        for e in m["estado_validacion"]:
            assert e["nivel"] in niveles and e["decision"] in ids
        assert any(e["contrato"] == "DMH" and e["modelo"] == "798 AC" and e["nivel"] == "aplicable"
                   for e in m["estado_validacion"]), m["id"]
