"""Fase 1: experimentos y modelos registrados en MLflow; el modelo vigente requiere promoción."""
from datetime import date

import pytest

from agentes.supervisor import Supervisor
from contratos.base import FaseFlujo, TipoFlujo
from contratos.supervisor import SupervisorInput
from tests.test_tracer_bullet import DATOS

pytest.importorskip("mlflow")
from core.registro_modelos import RegistroModelos  # noqa: E402


def _solicitud(tipo, rid):
    return SupervisorInput(request_id=rid, caso_uso_id="cu-motor", equipo="CAEX-101",
                           tipo_flujo=tipo, fecha_corte=date(2026, 1, 31))


@pytest.fixture
def registro(tmp_path):
    return RegistroModelos(f"sqlite:///{tmp_path / 'mlflow.db'}")


def test_entrenamiento_registra_candidato_sin_volverlo_vigente(registro):
    est = Supervisor(registro=registro).ejecutar_solicitud(
        _solicitud(TipoFlujo.ENTRENAMIENTO, "ent-1"), DATOS)
    assert est.fase == FaseFlujo.PENDIENTE_HUMANO
    reg = est.salidas["registro_modelo"]
    assert reg["alias"] == "candidato" and reg["version"] == "1"
    run = registro.cliente.get_run(reg["mlflow_run_id"])
    assert run.data.tags["request_id"] == "ent-1"
    assert run.data.params["fecha_corte"] == "2026-01-31"
    assert registro.cargar("motor_diesel", "candidato").version_modelo == "1"
    assert registro.cargar("motor_diesel") is None  # sin aprobación humana no hay vigente


def test_inferencia_usa_el_modelo_promovido(registro):
    sup = Supervisor(registro=registro)
    est = sup.ejecutar_solicitud(_solicitud(TipoFlujo.ENTRENAMIENTO, "ent-1"), DATOS)
    registro.promover("motor_diesel", est.salidas["registro_modelo"]["version"])
    inf = sup.ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA, "inf-1"), DATOS)
    assert inf.fase == FaseFlujo.PENDIENTE_HUMANO
    vigente = registro.cargar("motor_diesel")
    assert vigente.version_modelo == "1"
    assert vigente.variables == est.salidas["modelamiento"]["variables"]


def test_inferencia_sin_modelo_vigente_usa_baseline(registro):
    est = Supervisor(registro=registro).ejecutar_solicitud(
        _solicitud(TipoFlujo.INFERENCIA, "inf-1"), DATOS)
    assert est.fase == FaseFlujo.PENDIENTE_HUMANO
