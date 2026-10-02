import pytest
from pydantic import ValidationError

from agentes.base import BaseAgente, ErrorAgente
from agentes.supervisor import Estado, Supervisor
from contratos.agentes import Contexto, IngestaEntrada, IngestaSalida

CTX = Contexto(run_id="r1", componente="motor_diesel")
DATOS = [{"temp_refrigerante": 120.0, "presion_aceite": 300.0},
         {"temp_refrigerante": 95.0, "presion_aceite": 400.0}]


def test_flujo_completo():
    sup = Supervisor()
    res = sup.ejecutar(CTX, DATOS)
    assert res.exito
    assert sup.historial[-1] == Estado.FIN
    assert len(res.auditoria) == 9
    assert res.salidas["recomendacion"].acciones


def test_calidad_rechaza_fuera_de_rango():
    res = Supervisor().ejecutar(CTX, DATOS + [{"temp_refrigerante": 999, "presion_aceite": 1}])
    assert res.salidas["calidad"].n_rechazados == 1


def test_fallo_sin_datos_validos():
    sup = Supervisor()
    res = sup.ejecutar(CTX, [{"temp_refrigerante": 999, "presion_aceite": 1}])
    assert not res.exito and sup.historial[-1] == Estado.FALLO


def test_contrato_extra_prohibido():
    with pytest.raises(ValidationError):
        IngestaEntrada(contexto=CTX, registros=[], otro=1)


def test_base_agente_audita_errores():
    class Roto(BaseAgente):
        nombre, entrada, salida = "roto", IngestaEntrada, IngestaSalida

        def procesar(self, d):
            raise RuntimeError("boom")

    a = Roto()
    with pytest.raises(ErrorAgente):
        a.ejecutar(IngestaEntrada(contexto=CTX, registros=[]))
    assert a.auditoria[0].estado.value == "error"
