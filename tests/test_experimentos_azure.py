"""Los scripts de experimentos/azure corren sin Azure (cliente simulado y MLflow local)."""
import asyncio
from types import SimpleNamespace

import pytest

from experimentos.azure import p2_clasificar_causas as p2


class AgenteFalso:
    """Imita Agent.run de Agent Framework con salida estructurada y guarda lo que se le envió."""

    def __init__(self):
        self.enviados = []

    async def run(self, texto, options=None):
        self.enviados.append(texto)
        r = options["response_format"](grupo_falla="indeterminado", modos_fmea=[],
                                       requiere_modo_nuevo=False, confianza="baja",
                                       evidencia=[], justificacion="simulado")
        return SimpleNamespace(value=r, text=r.model_dump_json())


def test_p2_no_envia_identificadores_ni_la_propuesta_manual():
    agente = AgenteFalso()
    filas = asyncio.run(p2.evaluar(agente, repeticiones=2))
    assert len(filas) == 14 and all(f["consistencia"] == "2/2" for f in filas)
    texto = " ".join(agente.enviados)
    for prohibido in ("MH34", "SKH", "grupo_falla_propuesto", "modo_fmea_propuesto", "2024-"):
        assert prohibido not in texto
    assert "MFP-07" in p2.prompt_sistema()  # el FMEA va en las instrucciones del agente
    assert "Prueba 2" in p2.resumen(filas, "falso", 2)


def test_p3_instrucciones_con_fmea_y_caso_sin_identificadores():
    from experimentos.azure import p3_analisis_secuencial as p3

    inst = p3.instrucciones()
    assert list(inst) == ["evidencia", "fmea", "revisor"] and "MFP-01" in inst["fmea"]
    texto = p2.registro_tecnico(p3.leer_caso(4))
    assert "MH344" not in texto and "SKH" not in texto and "gripaje" in texto


def test_p1_flujo_completo_en_mlflow_local(tmp_path):
    pytest.importorskip("mlflow")
    from experimentos.azure import p1_registro_azureml as p1

    pasos = p1.ejecutar(f"sqlite:///{tmp_path / 'p1.db'}")
    assert all(p["ok"] for p in pasos.values()), pasos


def test_reintenta_solo_ante_429():
    llamadas = []

    async def llamada():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise RuntimeError("Error code: 429 - rate_limit_exceeded")
        return "ok"

    assert asyncio.run(p2.con_reintentos(llamada, intentos=4, espera_s=0)) == "ok"
    assert len(llamadas) == 3

    async def otro_error():
        raise ValueError("endpoint inválido")

    with pytest.raises(ValueError):
        asyncio.run(p2.con_reintentos(otro_error, intentos=4, espera_s=0))
