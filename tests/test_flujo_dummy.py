"""Criterio de salida Fase 1: flujo dummy completo del Supervisor."""
from datetime import date

import pytest

from agentes.supervisor import Supervisor
from contratos.base import Estado, FaseFlujo, TipoFlujo
from contratos.supervisor import SupervisorInput
from tests.test_tracer_bullet import DATOS, MALO

PASOS = {
    TipoFlujo.ENTRENAMIENTO: ["ingesta", "calidad", "variables", "modelamiento",
                              "validacion", "human_in_the_loop"],
    TipoFlujo.INFERENCIA: ["ingesta", "calidad", "variables", "inferencia",
                           "interpretacion", "recomendacion", "human_in_the_loop"],
}


def _solicitud(tipo, rid="req-1"):
    return SupervisorInput(request_id=rid, caso_uso_id="cu-motor", equipo="CAEX-101",
                           tipo_flujo=tipo, fecha_corte=date(2026, 1, 31))


@pytest.mark.parametrize("tipo", list(TipoFlujo))
def test_flujo_dummy_estado_cerrado_y_auditoria_completa(tipo):
    est = Supervisor().ejecutar_solicitud(_solicitud(tipo), DATOS)
    assert isinstance(est, Estado)
    assert est.cerrado and not est.errores
    assert est.fase == FaseFlujo.PENDIENTE_HUMANO
    assert est.pasos_completados == PASOS[tipo]
    assert [r.agente for r in est.auditoria] == PASOS[tipo]
    assert all(r.run_id == "req-1" and r.estado.value == "ok" for r in est.auditoria)
    Estado.model_validate(est.model_dump())


def test_flujo_se_detiene_si_calidad_rechaza():
    est = Supervisor().ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), [MALO])
    assert est.cerrado and est.fase == FaseFlujo.FALLIDO and est.errores
    assert "variables" not in est.pasos_completados
