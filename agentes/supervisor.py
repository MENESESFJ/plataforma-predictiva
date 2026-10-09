"""Supervisor: máquina de estados determinística que coordina el flujo."""
from enum import Enum
from typing import Dict, Optional

from agentes.base import BaseAgente, ErrorAgente
from agentes.calidad import AgenteCalidad
from agentes.componentes import cargar_bundle
from agentes.interpretacion import AgenteInterpretacion
from agentes.recomendacion import AgenteRecomendacion
from agentes.tracer import (
    AgenteIngesta, AgenteModelamiento, AgenteMonitoreo, AgenteValidacion, AgenteVariables,
)
from contratos.agentes import (
    CalidadEntrada, Contexto, EstadoEjecucion, IngestaEntrada, InferenciaEntrada,
    InterpretacionEntrada, ModeladoEntrada, ModeladoSalida, MonitoreoEntrada,
    RecomendacionEntrada, RegistroAuditoria, ValidacionEntrada, VariablesEntrada,
    VeredictoCalidad, ahora,
)
from contratos.base import Estado, FaseFlujo, TipoFlujo
from contratos.supervisor import SupervisorInput
from estado import RepositorioEstado
from inferencia.servicio import ServicioInferencia
from trazabilidad import RegistroTrazas


class Paso(str, Enum):
    INGESTA = "ingesta"
    CALIDAD = "calidad"
    VARIABLES = "variables"
    MODELAMIENTO = "modelamiento"
    VALIDACION = "validacion"
    INFERENCIA = "inferencia"
    INTERPRETACION = "interpretacion"
    RECOMENDACION = "recomendacion"
    MONITOREO = "monitoreo"


FLUJOS = {
    TipoFlujo.ENTRENAMIENTO: [Paso.INGESTA, Paso.CALIDAD, Paso.VARIABLES,
                              Paso.MODELAMIENTO, Paso.VALIDACION],
    TipoFlujo.INFERENCIA: [Paso.INGESTA, Paso.CALIDAD, Paso.VARIABLES, Paso.INFERENCIA,
                           Paso.INTERPRETACION, Paso.RECOMENDACION],
}


class Supervisor:
    def __init__(self, agentes: Dict[Paso, BaseAgente] = None,
                 repositorio: Optional[RepositorioEstado] = None,
                 trazas: Optional[RegistroTrazas] = None) -> None:
        self.agentes = agentes or {
            Paso.INGESTA: AgenteIngesta(), Paso.CALIDAD: AgenteCalidad(),
            Paso.VARIABLES: AgenteVariables(), Paso.MODELAMIENTO: AgenteModelamiento(),
            Paso.VALIDACION: AgenteValidacion(), Paso.INFERENCIA: ServicioInferencia(),
            Paso.INTERPRETACION: AgenteInterpretacion(),
            Paso.RECOMENDACION: AgenteRecomendacion(), Paso.MONITOREO: AgenteMonitoreo(),
        }
        self.repositorio = repositorio
        self.trazas = trazas

    def _entrada(self, paso: Paso, ctx: Contexto, s: dict):
        if paso == Paso.INGESTA:
            return IngestaEntrada(contexto=ctx, registros=s["registros"])
        if paso == Paso.CALIDAD:
            return CalidadEntrada(contexto=ctx, registros=s["ingesta"].registros)
        if paso == Paso.VARIABLES:
            return VariablesEntrada(contexto=ctx, registros=s["calidad"].registros_validos)
        if paso == Paso.MODELAMIENTO:
            return ModeladoEntrada(contexto=ctx, features=s["variables"].features)
        if paso == Paso.VALIDACION:
            m = s["modelamiento"]
            return ValidacionEntrada(contexto=ctx, modelo_id=m.modelo_id,
                                     version_modelo=m.version_modelo, metricas=m.metricas,
                                     variables=m.variables, supera_baseline=m.supera_baseline)
        if paso == Paso.INFERENCIA:
            return InferenciaEntrada(contexto=ctx, modelo_id=s["modelamiento"].modelo_id,
                                     variables_modelo=s["modelamiento"].variables,
                                     features=s["variables"].features)
        if paso == Paso.INTERPRETACION:
            i = s["inferencia"]
            return InterpretacionEntrada(contexto=ctx, riesgo=i.riesgo, shap=i.shap)
        if paso == Paso.RECOMENDACION:
            i = s["interpretacion"]
            return RecomendacionEntrada(contexto=ctx, severidad=i.nivel_riesgo,
                                        modo_falla=i.modo_falla,
                                        variables_influyentes=i.variables_influyentes)
        return MonitoreoEntrada(contexto=ctx, riesgo=s["inferencia"].riesgo,
                                acciones=s["recomendacion"].acciones)

    def _modelo_vigente(self, ctx: Contexto) -> ModeladoSalida:
        # stub del registro MLflow: variables del catálogo del componente
        nombres = sorted(f["nombre"] for f in cargar_bundle(
            ctx.ruta_componentes, ctx.componente)["feature_catalog"]["features"])
        return ModeladoSalida(modelo_id=f"{ctx.componente}-baseline", version_modelo="0.1.0",
                              metricas={}, variables=nombres)

    def _trazar(self, est: Estado, registros) -> None:
        for r in registros:
            est.auditoria.append(r)
            if self.trazas:
                self.trazas.registrar(r)

    def _persistir(self, est: Estado) -> None:
        if self.repositorio:
            self.repositorio.guardar(est)

    def ejecutar_solicitud(self, entrada: SupervisorInput, registros: list) -> Estado:
        """Flujo de entrenamiento o inferencia; devuelve el Estado global cerrado.

        Con repositorio y registro de trazas, el Estado se persiste tras cada paso y
        es reconstruible desde su request_id.
        """
        if self.repositorio and self.repositorio.existe(entrada.request_id):
            raise ValueError(f"request_id ya registrado: {entrada.request_id}")
        ctx = Contexto(run_id=entrada.request_id, componente=entrada.componente,
                       fecha_corte=entrada.fecha_corte,
                       ruta_componentes=entrada.ruta_componentes)
        est = Estado(request_id=entrada.request_id, caso_uso_id=entrada.caso_uso_id,
                     equipo=entrada.equipo, componente=entrada.componente,
                     tipo_flujo=entrada.tipo_flujo, fecha_corte=entrada.fecha_corte)
        self._persistir(est)
        s: dict = {"registros": registros}
        try:
            for paso in FLUJOS[entrada.tipo_flujo]:
                if paso == Paso.INFERENCIA and "modelamiento" not in s:
                    s["modelamiento"] = self._modelo_vigente(ctx)
                agente = self.agentes[paso]
                datos = self._entrada(paso, ctx, s)
                n = len(agente.auditoria)
                try:
                    s[paso.value] = agente.ejecutar(datos, ctx.run_id)
                finally:
                    # la traza del agente se registra también cuando falla
                    self._trazar(est, agente.auditoria[n:])
                est.pasos_completados.append(paso.value)
                est.salidas[paso.value] = s[paso.value]
                self._persistir(est)
                if paso == Paso.CALIDAD and s[paso.value].veredicto == VeredictoCalidad.RECHAZADO:
                    raise ValueError("calidad rechazada: " + "; ".join(s[paso.value].violaciones))
                if paso == Paso.VALIDACION and not s[paso.value].aprobado:
                    raise ValueError("modelo rechazado: " + "; ".join(s[paso.value].motivos))
            t = ahora()
            est.pasos_completados.append("human_in_the_loop")
            est.fase = FaseFlujo.PENDIENTE_HUMANO
            self._trazar(est, [RegistroAuditoria(
                run_id=ctx.run_id, agente="human_in_the_loop", estado=EstadoEjecucion.OK,
                inicio=t, fin=t, duracion_ms=0.0)])
        except (ErrorAgente, ValueError) as exc:
            est.errores.append(str(exc))
            est.fase = FaseFlujo.FALLIDO
        est.cerrado = True
        self._persistir(est)
        return Estado.model_validate_json(est.model_dump_json())
