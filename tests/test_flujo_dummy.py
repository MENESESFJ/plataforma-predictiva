"""Criterio de salida Fase 1: el flujo se ejecuta, persiste su Estado y es reconstruible
desde su request_id."""
from datetime import date

import pytest

from agentes.base import BaseAgente
from agentes.supervisor import Paso, Supervisor
from contratos.agentes import InterpretacionEntrada, InterpretacionSalida
from contratos.base import Estado, FaseFlujo, TipoFlujo
from contratos.supervisor import SupervisorInput
from estado import RepositorioEstado
from tests.test_tracer_bullet import DATOS, MALO
from trazabilidad import RegistroTrazas

PASOS = {
    TipoFlujo.ENTRENAMIENTO: ["ingesta", "calidad", "variables", "modelamiento",
                              "validacion", "human_in_the_loop"],
    TipoFlujo.INFERENCIA: ["ingesta", "calidad", "variables", "inferencia",
                           "interpretacion", "recomendacion", "human_in_the_loop"],
}


def _solicitud(tipo, rid="req-1"):
    return SupervisorInput(request_id=rid, caso_uso_id="cu-motor", equipo="CAEX-101",
                           tipo_flujo=tipo, fecha_corte=date(2026, 1, 31))


def _supervisor_persistente(ruta):
    return Supervisor(repositorio=RepositorioEstado(str(ruta)), trazas=RegistroTrazas(str(ruta)))


@pytest.mark.parametrize("tipo", list(TipoFlujo))
def test_flujo_dummy_estado_cerrado_y_auditoria_completa(tipo):
    est = Supervisor().ejecutar_solicitud(_solicitud(tipo), DATOS)
    assert isinstance(est, Estado)
    assert est.cerrado and not est.errores
    assert est.fase == FaseFlujo.PENDIENTE_HUMANO
    assert est.pasos_completados == PASOS[tipo]
    assert [r.agente for r in est.auditoria] == PASOS[tipo]
    assert all(r.run_id == "req-1" and r.estado.value == "ok" for r in est.auditoria)


def test_flujo_inferencia_entrega_acciones_para_revision():
    est = Supervisor().ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), DATOS)
    interp, recom = est.salidas["interpretacion"], est.salidas["recomendacion"]
    assert interp["diagnostico"]
    assert recom["acciones"]
    assert all(a["severidad"] == interp["nivel_riesgo"] for a in recom["acciones"])
    assert all(a["estado_revision"] == "pendiente_especialista" for a in recom["acciones"])


def test_flujo_inferencia_riesgo_alto_identifica_modo_fmea():
    alto = [{"temp_refrigerante": 140.0, "presion_carter": 90.0, "fe_ppm": 450.0,
             "cu_ppm": 190.0, "pqi": 900.0}]
    est = Supervisor().ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), alto)
    interp = est.salidas["interpretacion"]
    assert interp["nivel_riesgo"] in ("alta", "critica")
    assert interp["id_modo_falla"] and interp["modo_falla"]
    # sin código SMCS en el contexto, la compatibilidad no se evalúa ni se inventa
    assert [c["interpretacion"] for c in interp["compatibilidades_smcs"]] == ["no_evaluado"]
    assert all(a["severidad"] == interp["nivel_riesgo"]
               for a in est.salidas["recomendacion"]["acciones"])


def test_flujo_se_detiene_si_calidad_rechaza():
    est = Supervisor().ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), [MALO])
    assert est.cerrado and est.fase == FaseFlujo.FALLIDO
    assert est.errores[0].startswith("calidad rechazada")
    assert "variables" not in est.pasos_completados


def test_veredicto_rechazado_detiene_flujo_aunque_haya_registros_validos():
    est = Supervisor().ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), DATOS + [MALO] * 2)
    assert est.salidas["calidad"]["registros_validos"]
    assert est.fase == FaseFlujo.FALLIDO
    assert "variables" not in est.pasos_completados


@pytest.mark.parametrize("tipo", list(TipoFlujo))
def test_estado_reconstruible_desde_request_id(tipo, tmp_path):
    ruta = tmp_path / "plataforma.db"
    est = _supervisor_persistente(ruta).ejecutar_solicitud(_solicitud(tipo), DATOS)
    # conexiones nuevas: simula reconstrucción desde otro proceso
    assert RepositorioEstado(str(ruta)).cargar("req-1") == est
    assert RegistroTrazas(str(ruta)).por_run("req-1") == est.auditoria
    assert RepositorioEstado(str(ruta)).cargar("otro") is None


def test_falla_de_agente_queda_persistida_con_su_traza(tmp_path):
    class InterpretacionRota(BaseAgente):
        nombre, entrada, salida = "interpretacion", InterpretacionEntrada, InterpretacionSalida

        def procesar(self, d):
            raise RuntimeError("boom")

    ruta = tmp_path / "plataforma.db"
    sup = _supervisor_persistente(ruta)
    sup.agentes[Paso.INTERPRETACION] = InterpretacionRota()
    est = sup.ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), DATOS)
    assert est.fase == FaseFlujo.FALLIDO and "boom" in est.errores[0]
    assert "interpretacion" not in est.pasos_completados
    trazas = RegistroTrazas(str(ruta)).por_run("req-1")
    assert trazas[-1].agente == "interpretacion" and trazas[-1].estado.value == "error"
    assert RepositorioEstado(str(ruta)).cargar("req-1") == est


def test_request_id_duplicado_se_rechaza(tmp_path):
    sup = _supervisor_persistente(tmp_path / "plataforma.db")
    sup.ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), DATOS)
    with pytest.raises(ValueError, match="request_id ya registrado"):
        sup.ejecutar_solicitud(_solicitud(TipoFlujo.INFERENCIA), DATOS)
