"""Implementaciones mínimas (Tracer Bullet) de los agentes y del servicio de inferencia."""
import math

from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import (
    CalidadEntrada, CalidadSalida, IngestaEntrada, IngestaSalida,
    InferenciaEntrada, InferenciaSalida, InterpretacionEntrada,
    InterpretacionSalida, ModeladoEntrada, ModeladoSalida, MonitoreoEntrada,
    MonitoreoSalida, RecomendacionEntrada, RecomendacionSalida, Severidad,
    ValidacionEntrada, ValidacionSalida, VariablesEntrada, VariablesSalida,
)


def _bundle(ctx):
    return cargar_bundle(ctx.ruta_componentes, ctx.componente)


class AgenteIngesta(BaseAgente):
    nombre, entrada, salida = "ingesta", IngestaEntrada, IngestaSalida

    def procesar(self, d):
        return IngestaSalida(registros=d.registros, n_registros=len(d.registros))


class AgenteCalidad(BaseAgente):
    nombre, entrada, salida = "calidad", CalidadEntrada, CalidadSalida

    def procesar(self, d):
        reglas = _bundle(d.contexto)["quality_rules"]["reglas"]
        validos, violaciones = [], []
        for i, r in enumerate(d.registros):
            malo = [x["variable"] for x in reglas
                    if not isinstance(r.get(x["variable"]), (int, float))
                    or not x["min"] <= r[x["variable"]] <= x["max"]]
            if malo:
                violaciones.append(f"registro {i}: {', '.join(malo)}")
            else:
                validos.append(r)
        return CalidadSalida(registros_validos=validos,
                             n_rechazados=len(d.registros) - len(validos),
                             violaciones=violaciones)


class AgenteVariables(BaseAgente):
    nombre, entrada, salida = "variables", VariablesEntrada, VariablesSalida

    def procesar(self, d):
        nombres = [f["nombre"] for f in _bundle(d.contexto)["feature_catalog"]["features"]]
        return VariablesSalida(
            features=[{n: float(r[n]) for n in nombres} for r in d.registros],
            nombres=nombres)


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
        return ValidacionSalida(aprobado=not motivos, motivos=motivos)


class ServicioInferencia(BaseAgente):
    """Determinístico: riesgo logístico lineal y contribuciones aditivas tipo SHAP."""
    nombre, entrada, salida = "inferencia", InferenciaEntrada, InferenciaSalida

    def procesar(self, d):
        rangos = {x["variable"]: (x["min"], x["max"])
                  for x in _bundle(d.contexto)["quality_rules"]["reglas"]}
        riesgo, shap = [], []
        for f in d.features:
            if set(f) != set(d.variables_modelo):
                raise ValueError("variables incompatibles con el modelo vigente")
            contrib = {}
            for k, v in f.items():
                lo, hi = rangos[k]
                contrib[k] = (v - lo) / (hi - lo) - 0.5
            riesgo.append(1 / (1 + math.exp(-4 * sum(contrib.values()))))
            shap.append(contrib)
        return InferenciaSalida(riesgo=riesgo, shap=shap)


class AgenteInterpretacion(BaseAgente):
    nombre, entrada, salida = "interpretacion", InterpretacionEntrada, InterpretacionSalida

    def procesar(self, d):
        r = max(d.riesgo, default=0.0)
        sev = (Severidad.CRITICA if r >= 0.9 else Severidad.ALTA if r >= 0.7
               else Severidad.MEDIA if r >= 0.4 else Severidad.BAJA)
        pesos = {}
        for s in d.shap:
            for k, v in s.items():
                pesos[k] = pesos.get(k, 0.0) + abs(v)
        influyentes = sorted(pesos, key=pesos.get, reverse=True)
        modo = None
        if influyentes and sev in (Severidad.ALTA, Severidad.CRITICA):
            for m in _bundle(d.contexto)["fmea"]["modos_falla"]:
                if influyentes[0] in m["variables"]:
                    modo = m["nombre"]
                    break
        return InterpretacionSalida(riesgo_max=r, severidad=sev,
                                    variables_influyentes=influyentes, modo_falla=modo)


class AgenteRecomendacion(BaseAgente):
    nombre, entrada, salida = "recomendacion", RecomendacionEntrada, RecomendacionSalida

    def procesar(self, d):
        cat = _bundle(d.contexto)["action_catalog"]["acciones"]
        return RecomendacionSalida(
            acciones=[a["accion"] for a in cat if a["severidad"] == d.severidad.value])


class AgenteMonitoreo(BaseAgente):
    nombre, entrada, salida = "monitoreo", MonitoreoEntrada, MonitoreoSalida

    def procesar(self, d):
        deriva = bool(d.riesgo) and sum(d.riesgo) / len(d.riesgo) > 0.8
        return MonitoreoSalida(deriva_detectada=deriva,
                               feedback=["revisar modelo"] if deriva else [])
