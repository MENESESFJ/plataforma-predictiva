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


def _secciones(ruta):
    """(autor, texto) de cada sección '## autor' de un resultado de la prueba 3."""
    partes = ruta.read_text(encoding="utf-8").split("\n## ")[1:]
    return [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1].strip()) for p in partes]


ESPERADO_ECO = {  # corridas reales del 2026-11-24, copiadas en tests/fixtures/p3_eco
    "corrida2_caso0": [], "corrida2_caso3": ["revisor"], "corrida2_caso4": ["fmea", "revisor"],
    "corrida3_caso0": [], "corrida3_caso3": ["fmea"], "corrida3_caso4": [],
    "corrida5_caso0": ["fmea", "revisor"],                      # código anterior, sin detección
    "corrida6_caso0": [], "corrida6_caso3": [], "corrida6_caso4": [],  # versión nueva (PR #16)
}


@pytest.mark.parametrize("nombre,esperado", sorted(ESPERADO_ECO.items()))
def test_p3_detecta_eco_en_corridas_reales(nombre, esperado):
    """Copias reales: corrida 2 caso 4 (fmea y revisor textuales), caso 3 (revisor parafrasea, 0,84);
    corrida 3 caso 3 (fmea copia la evidencia). Las respuestas normales están bajo 0,25."""
    from pathlib import Path

    from experimentos.azure import p3_analisis_secuencial as p3

    ruta = Path(__file__).parent / "fixtures" / "p3_eco" / f"{nombre}.md"
    assert p3.detectar_eco(_secciones(ruta)) == esperado


def test_p3_sin_eco_e_instruccion_de_no_repetir():
    from experimentos.azure import p3_analisis_secuencial as p3

    assert p3.detectar_eco([("evidencia", "hechos A"), ("fmea", "modos B y modo nuevo C"),
                            ("revisor", "lo sustentado y lo supuesto")]) == []
    assert "no copies" in p3.instrucciones()["revisor"]
