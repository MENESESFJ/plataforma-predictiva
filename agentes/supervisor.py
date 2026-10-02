"""Supervisor: máquina de estados determinística que coordina el flujo."""
from enum import Enum
from typing import Dict, List

from agentes.base import BaseAgente, ErrorAgente
from agentes.tracer import (
    AgenteCalidad, AgenteIngesta, AgenteInterpretacion, AgenteModelamiento,
    AgenteMonitoreo, AgenteRecomendacion, AgenteValidacion, AgenteVariables,
    ServicioInferencia,
)
from contratos.agentes import (
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
