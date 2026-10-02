import pytest
from pydantic import ValidationError

from agentes.base import BaseAgente, ErrorAgente
from agentes.supervisor import Estado, Supervisor
from contratos.agentes import Contexto, IngestaEntrada, IngestaSalida

CTX = Contexto(run_id="r1", componente="motor_diesel")
DATOS = [{"temp_refrigerante": 120.0, "presion_carter": 30.0, "fe_ppm": 80.0, "cu_ppm": 20.0, "pqi": 150.0},
         {"temp_refrigerante": 95.0, "presion_carter": 40.0, "fe_ppm": 50.0, "cu_ppm": 10.0, "pqi": 90.0}]
MALO = {"temp_refrigerante": 999, "presion_carter": 1, "fe_ppm": 1, "cu_ppm": 1, "pqi": 1}


def test_flujo_completo():
    sup = Supervisor()
    res = sup.ejecutar(CTX, DATOS)
    assert res.exito
    assert sup.historial[-1] == Estado.FIN
    assert len(res.auditoria) == 9
    assert res.salidas["recomendacion"].acciones


def test_calidad_rechaza_fuera_de_rango():
    res = Supervisor().ejecutar(CTX, DATOS + [MALO])
    assert res.salidas["calidad"].n_rechazados == 1


def test_fallo_sin_datos_validos():
    sup = Supervisor()
    res = sup.ejecutar(CTX, [MALO])
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
