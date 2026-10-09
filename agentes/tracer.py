"""Implementaciones mínimas (stubs) de los agentes que aún no tienen versión productiva.

Calidad, Interpretación, Recomendación y el Servicio de Inferencia viven en sus
propios módulos. Estos stubs se reemplazan en las Fases 2 (Ingesta), 3 (Variables,
Modelamiento, Validación) y 7 (Monitoreo).
"""
import hashlib
import json

from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import (
    IngestaEntrada, IngestaSalida, ModeladoEntrada, ModeladoSalida,
    MonitoreoEntrada, MonitoreoSalida, ValidacionEntrada, ValidacionSalida,
    VariablesEntrada, VariablesSalida,
)


def _hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class AgenteIngesta(BaseAgente):
    """Stub: recibe los registros ya extraídos; calcula hash y dataset_id determinísticos."""
    nombre, entrada, salida = "ingesta", IngestaEntrada, IngestaSalida

    def procesar(self, d):
        h = _hash(d.registros)
        ctx = d.contexto
        return IngestaSalida(
            dataset_id=f"{ctx.componente}-{ctx.fecha_corte:%Y%m%d}-{h[:12]}",
            hash_snapshot=h, n_registros=len(d.registros), registros=d.registros,
            fuentes_metadata={"origen": "registros_en_memoria"})


class AgenteVariables(BaseAgente):
    nombre, entrada, salida = "variables", VariablesEntrada, VariablesSalida

    def procesar(self, d):
        nombres = [f["nombre"] for f in cargar_bundle(
            d.contexto.ruta_componentes, d.contexto.componente)["feature_catalog"]["features"]]
        features = [{n: float(r[n]) for n in nombres} for r in d.registros]
        return VariablesSalida(feature_set_id=f"{d.contexto.componente}-fs-{_hash(features)[:12]}",
                               features=features, nombres=nombres)


class AgenteModelamiento(BaseAgente):
    nombre, entrada, salida = "modelamiento", ModeladoEntrada, ModeladoSalida

    def procesar(self, d):
        variables = sorted(d.features[0]) if d.features else []
        return ModeladoSalida(modelo_id=f"{d.contexto.componente}-baseline",
                              version_modelo="0.1.0",
                              metricas={"n_entrenamiento": float(len(d.features))},
                              variables=variables)


class AgenteValidacion(BaseAgente):
    nombre, entrada, salida = "validacion", ValidacionEntrada, ValidacionSalida

    def procesar(self, d):
        motivos = []
        if not d.variables:
            motivos.append("modelo sin variables")
        if d.metricas.get("n_entrenamiento", 0) < 1:
            motivos.append("sin datos de entrenamiento")
        return ValidacionSalida(aprobado=not motivos,
                                veredicto="rechazado" if motivos else "aprobado",
                                motivos=motivos)


class AgenteMonitoreo(BaseAgente):
    nombre, entrada, salida = "monitoreo", MonitoreoEntrada, MonitoreoSalida

    def procesar(self, d):
        deriva = bool(d.riesgo) and sum(d.riesgo) / len(d.riesgo) > 0.8
        return MonitoreoSalida(deriva_detectada=deriva,
                               feedback=["revisar modelo"] if deriva else [])
