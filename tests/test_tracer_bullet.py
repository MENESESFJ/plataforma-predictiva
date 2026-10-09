import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentes.base import BaseAgente, ErrorAgente
from agentes.calidad import AgenteCalidad
from agentes.recomendacion import AgenteRecomendacion
from agentes.tracer import AgenteIngesta
from contratos.agentes import (
    CalidadEntrada, Contexto, IngestaEntrada, IngestaSalida, RecomendacionEntrada,
    Severidad, VeredictoCalidad,
)

CTX = Contexto(run_id="r1", componente="motor_diesel", fecha_corte=date(2026, 1, 31))
DATOS = [{"temp_refrigerante": 120.0, "presion_carter": 30.0, "fe_ppm": 80.0, "cu_ppm": 20.0, "pqi": 150.0},
         {"temp_refrigerante": 95.0, "presion_carter": 40.0, "fe_ppm": 50.0, "cu_ppm": 10.0, "pqi": 90.0}]
MALO = {"temp_refrigerante": 999, "presion_carter": 1, "fe_ppm": 1, "cu_ppm": 1, "pqi": 1}


def test_contrato_extra_prohibido():
    with pytest.raises(ValidationError):
        IngestaEntrada(contexto=CTX, registros=[], otro=1)


def test_contexto_exige_fecha_corte():
    with pytest.raises(ValidationError):
        Contexto(run_id="r1", componente="motor_diesel")


def test_base_agente_audita_errores():
    class Roto(BaseAgente):
        nombre, entrada, salida = "roto", IngestaEntrada, IngestaSalida

        def procesar(self, d):
            raise RuntimeError("boom")

    a = Roto()
    with pytest.raises(ErrorAgente):
        a.ejecutar(IngestaEntrada(contexto=CTX, registros=[]))
    assert a.auditoria[0].estado.value == "error"


def test_ingesta_snapshot_deterministico():
    a = AgenteIngesta().ejecutar(IngestaEntrada(contexto=CTX, registros=DATOS))
    b = AgenteIngesta().ejecutar(IngestaEntrada(contexto=CTX, registros=[dict(r) for r in DATOS]))
    c = AgenteIngesta().ejecutar(IngestaEntrada(contexto=CTX, registros=DATOS[:1]))
    assert a.hash_snapshot == b.hash_snapshot and a.dataset_id == b.dataset_id
    assert a.hash_snapshot != c.hash_snapshot
    assert a.dataset_id.startswith("motor_diesel-20260131-")


def test_calidad_rechaza_fuera_de_rango():
    res = AgenteCalidad().ejecutar(CalidadEntrada(contexto=CTX, registros=DATOS + [MALO]))
    assert res.n_rechazados == 1 and len(res.registros_validos) == 2


def test_calidad_veredictos():
    calidad = AgenteCalidad()
    assert calidad.ejecutar(CalidadEntrada(contexto=CTX, registros=DATOS)).veredicto \
        == VeredictoCalidad.APROBADO
    assert calidad.ejecutar(CalidadEntrada(contexto=CTX, registros=[MALO])).veredicto \
        == VeredictoCalidad.RECHAZADO
    assert calidad.ejecutar(CalidadEntrada(contexto=CTX, registros=[])).veredicto \
        == VeredictoCalidad.RECHAZADO


def test_recomendacion_solo_acciones_del_catalogo():
    catalogo = json.loads(Path("components/motor_diesel/action_catalog.json").read_text("utf-8"))
    ids = {a["id"] for a in catalogo["acciones"]}
    for sev in Severidad:
        res = AgenteRecomendacion().ejecutar(RecomendacionEntrada(contexto=CTX, severidad=sev))
        assert res.acciones and all(a.id in ids for a in res.acciones)
        assert all(a.severidad == sev.value for a in res.acciones)
        assert all(a.estado_revision == "pendiente_especialista" for a in res.acciones)


def test_recomendacion_sin_accion_para_severidad_falla(tmp_path):
    shutil.copytree("components/motor_diesel", tmp_path / "motor_diesel")
    ruta = tmp_path / "motor_diesel" / "action_catalog.json"
    catalogo = json.loads(ruta.read_text("utf-8"))
    catalogo["acciones"] = [a for a in catalogo["acciones"] if a["severidad"] != "critica"]
    ruta.write_text(json.dumps(catalogo), "utf-8")
    ctx = CTX.model_copy(update={"ruta_componentes": str(tmp_path)})
    with pytest.raises(ErrorAgente, match="sin entrada para severidad 'critica'"):
        AgenteRecomendacion().ejecutar(
            RecomendacionEntrada(contexto=ctx, severidad=Severidad.CRITICA))
