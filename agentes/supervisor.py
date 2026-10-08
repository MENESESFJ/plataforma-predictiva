"""Supervisor: máquina de estados determinística que coordina el flujo."""
from enum import Enum
from typing import Dict, List

from agentes.base import BaseAgente, ErrorAgente
from agentes.tracer import (
    AgenteCalidad, AgenteIngesta, AgenteInterpretacion, AgenteModelamiento,
    AgenteMonitoreo, AgenteRecomendacion, AgenteValidacion, AgenteVariables,
    ServicioInferencia,
)
from contratos.base import Estado as EstadoGlobal, FaseFlujo, TipoFlujo
from contratos.supervisor import SupervisorInput
from contratos.agentes import (
    EstadoEjecucion, ModeladoSalida, RegistroAuditoria, ahora,
    CalidadEntrada, Contexto, IngestaEntrada, InferenciaEntrada,
    InterpretacionEntrada, ModeladoEntrada, MonitoreoEntrada, RecomendacionEntrada,
    ResultadoFlujo, ValidacionEntrada, VariablesEntrada,
)


class Estado(str, Enum):
    INGESTA = "ingesta"
    CALIDAD = "calidad"
    VARIABLES = "variables"
    MODELAMIENTO = "modelamiento"
    VALIDACION = "validacion"
    INFERENCIA = "inferencia"
    INTERPRETACION = "interpretacion"
    RECOMENDACION = "recomendacion"
    MONITOREO = "monitoreo"
    FIN = "fin"
    FALLO = "fallo"


SECUENCIA = [Estado.INGESTA, Estado.CALIDAD, Estado.VARIABLES, Estado.MODELAMIENTO,
             Estado.VALIDACION, Estado.INFERENCIA, Estado.INTERPRETACION,
             Estado.RECOMENDACION, Estado.MONITOREO, Estado.FIN]


class Supervisor:
    def __init__(self, agentes: Dict[Estado, BaseAgente] = None) -> None:
        self.agentes = agentes or {
            Estado.INGESTA: AgenteIngesta(), Estado.CALIDAD: AgenteCalidad(),
            Estado.VARIABLES: AgenteVariables(), Estado.MODELAMIENTO: AgenteModelamiento(),
            Estado.VALIDACION: AgenteValidacion(), Estado.INFERENCIA: ServicioInferencia(),
            Estado.INTERPRETACION: AgenteInterpretacion(),
            Estado.RECOMENDACION: AgenteRecomendacion(), Estado.MONITOREO: AgenteMonitoreo(),
        }
        self.historial: List[Estado] = []

    def _entrada(self, estado: Estado, ctx: Contexto, s: dict):
        if estado == Estado.INGESTA:
            return IngestaEntrada(contexto=ctx, registros=s["registros"])
        if estado == Estado.CALIDAD:
            return CalidadEntrada(contexto=ctx, registros=s["ingesta"].registros)
        if estado == Estado.VARIABLES:
            return VariablesEntrada(contexto=ctx, registros=s["calidad"].registros_validos)
        if estado == Estado.MODELAMIENTO:
            return ModeladoEntrada(contexto=ctx, features=s["variables"].features)
        if estado == Estado.VALIDACION:
            m = s["modelamiento"]
            return ValidacionEntrada(contexto=ctx, modelo_id=m.modelo_id,
                                     version_modelo=m.version_modelo,
                                     metricas=m.metricas, variables=m.variables)
        if estado == Estado.INFERENCIA:
            return InferenciaEntrada(contexto=ctx, modelo_id=s["modelamiento"].modelo_id,
                                     variables_modelo=s["modelamiento"].variables,
                                     features=s["variables"].features)
        if estado == Estado.INTERPRETACION:
            i = s["inferencia"]
            return InterpretacionEntrada(contexto=ctx, riesgo=i.riesgo, shap=i.shap)
        if estado == Estado.RECOMENDACION:
            i = s["interpretacion"]
            return RecomendacionEntrada(contexto=ctx, severidad=i.severidad,
                                        modo_falla=i.modo_falla)
        return MonitoreoEntrada(contexto=ctx, riesgo=s["inferencia"].riesgo,
                                acciones=s["recomendacion"].acciones)

    def ejecutar(self, ctx: Contexto, registros: list) -> ResultadoFlujo:
        salidas: dict = {"registros": registros}
        self.historial = []
        estado = SECUENCIA[0]
        while estado not in (Estado.FIN, Estado.FALLO):
            self.historial.append(estado)
            agente = self.agentes[estado]
            try:
                salidas[estado.value] = agente.ejecutar(self._entrada(estado, ctx, salidas),
                                                        ctx.run_id)
                if estado == Estado.VALIDACION and not salidas[estado.value].aprobado:
                    raise ValueError("modelo no aprobado: " + "; ".join(salidas[estado.value].motivos))
            except (ErrorAgente, ValueError):
                estado = Estado.FALLO
                break
            estado = SECUENCIA[SECUENCIA.index(estado) + 1]
        self.historial.append(estado)
        auditoria = [r for a in self.agentes.values() for r in a.auditoria
                     if r.run_id == ctx.run_id]
        auditoria.sort(key=lambda r: r.inicio)
        salidas.pop("registros")
        return ResultadoFlujo(run_id=ctx.run_id, exito=estado == Estado.FIN,
                              salidas=salidas, auditoria=auditoria)

    FLUJOS = {
        TipoFlujo.ENTRENAMIENTO: [Estado.INGESTA, Estado.CALIDAD, Estado.VARIABLES,
                                  Estado.MODELAMIENTO, Estado.VALIDACION],
        TipoFlujo.INFERENCIA: [Estado.INGESTA, Estado.CALIDAD, Estado.VARIABLES,
                               Estado.INFERENCIA, Estado.INTERPRETACION,
                               Estado.RECOMENDACION],
    }

    def ejecutar_solicitud(self, entrada: SupervisorInput, registros: list) -> EstadoGlobal:
        """Flujo de entrenamiento o inferencia; devuelve el Estado global cerrado."""
        ctx = Contexto(run_id=entrada.request_id, componente=entrada.componente,
                       ruta_componentes=entrada.ruta_componentes)
        est = EstadoGlobal(request_id=entrada.request_id, caso_uso_id=entrada.caso_uso_id,
                           equipo=entrada.equipo, componente=entrada.componente,
                           tipo_flujo=entrada.tipo_flujo, fecha_corte=entrada.fecha_corte)
        s: dict = {"registros": registros}
        try:
            for paso in self.FLUJOS[entrada.tipo_flujo]:
                if paso == Estado.INFERENCIA and "modelamiento" not in s:
                    # modelo vigente (stub del registro MLflow): variables del catálogo
                    from agentes.componentes import cargar_bundle
                    nombres = sorted(f["nombre"] for f in cargar_bundle(
                        ctx.ruta_componentes, ctx.componente)["feature_catalog"]["features"])
                    s["modelamiento"] = ModeladoSalida(
                        modelo_id=f"{ctx.componente}-baseline", version_modelo="0.1.0",
                        metricas={}, variables=nombres)
                s[paso.value] = self.agentes[paso].ejecutar(
                    self._entrada(paso, ctx, s), ctx.run_id)
                est.pasos_completados.append(paso.value)
                est.salidas[paso.value] = s[paso.value]
                if paso == Estado.CALIDAD and not s[paso.value].registros_validos:
                    raise ValueError("calidad rechazada: sin registros válidos")
                if paso == Estado.VALIDACION and not s[paso.value].aprobado:
                    raise ValueError("modelo rechazado: " + "; ".join(s[paso.value].motivos))
            t = ahora()
            est.auditoria.append(RegistroAuditoria(
                run_id=ctx.run_id, agente="human_in_the_loop", estado=EstadoEjecucion.OK,
                inicio=t, fin=t, duracion_ms=0.0))
            est.pasos_completados.append("human_in_the_loop")
            est.fase = FaseFlujo.PENDIENTE_HUMANO
        except (ErrorAgente, ValueError) as exc:
            est.errores.append(str(exc))
            est.fase = FaseFlujo.FALLIDO
        pasos = {p.value for p in self.FLUJOS[entrada.tipo_flujo]}
        est.auditoria = sorted(
            [r for a in self.agentes.values() for r in a.auditoria
             if r.run_id == ctx.run_id and r.agente in pasos] + est.auditoria,
            key=lambda r: r.inicio)
        est.cerrado = True
        return EstadoGlobal.model_validate(est.model_dump())
