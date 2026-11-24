"""Los scripts de experimentos/azure corren sin Azure (cliente simulado y MLflow local)."""
from types import SimpleNamespace

import pytest

from experimentos.azure import p2_clasificar_causas as p2


class ClienteFalso:
    """Imita client.chat.completions.parse y guarda lo que se le envió."""

    def __init__(self):
        self.enviados = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(parse=self._parse))

    def _parse(self, model, messages, response_format):
        self.enviados.append(messages)
        r = response_format(grupo_falla="indeterminado", modos_fmea=[], requiere_modo_nuevo=False,
                            confianza="baja", evidencia=[], justificacion="simulado")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=r))])


def test_p2_no_envia_identificadores_ni_la_propuesta_manual():
    cliente = ClienteFalso()
    filas = p2.evaluar(cliente, "falso", repeticiones=2)
    assert len(filas) == 14 and all(f["consistencia"] == "2/2" for f in filas)
    texto = " ".join(m["content"] for msgs in cliente.enviados for m in msgs if m["role"] == "user")
    for prohibido in ("MH34", "SKH", "grupo_falla_propuesto", "modo_fmea_propuesto", "2024-"):
        assert prohibido not in texto
    assert "MFP-07" in cliente.enviados[0][0]["content"]  # el FMEA va en el prompt de sistema
    assert "Prueba 2" in p2.resumen(filas, "falso", 2)


def test_p1_flujo_completo_en_mlflow_local(tmp_path):
    pytest.importorskip("mlflow")
    from experimentos.azure import p1_registro_azureml as p1

    pasos = p1.ejecutar(f"sqlite:///{tmp_path / 'p1.db'}")
    assert all(p["ok"] for p in pasos.values()), pasos
