"""Contratos Pydantic versionados para los agentes y el servicio de inferencia."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

VERSION_CONTRATOS = "1.1.0"


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_contrato: str = VERSION_CONTRATOS


class EstadoEjecucion(str, Enum):
    OK = "ok"
    ERROR = "error"


class Severidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class VeredictoCalidad(str, Enum):
    APROBADO = "aprobado"
    APROBADO_CON_OBSERVACIONES = "aprobado_con_observaciones"
    RECHAZADO = "rechazado"


class Contexto(Contrato):
    run_id: str
    componente: str
    fecha_corte: date
    ruta_componentes: str = "components"


# 2. Ingesta
class IngestaEntrada(Contrato):
    contexto: Contexto
    registros: List[Dict[str, Any]]


class IngestaSalida(Contrato):
    dataset_id: str
    hash_snapshot: str
    n_registros: int
    registros: List[Dict[str, Any]]
    fuentes_metadata: Dict[str, Any] = Field(default_factory=dict)


# 3. Calidad
class CalidadEntrada(Contrato):
    contexto: Contexto
    registros: List[Dict[str, Any]]


class CalidadSalida(Contrato):
    veredicto: VeredictoCalidad
    score_calidad: float = Field(ge=0.0, le=100.0)
    registros_validos: List[Dict[str, Any]]
    n_rechazados: int
    violaciones: List[str] = Field(default_factory=list)


# 4. Ingeniería de variables
class VariablesEntrada(Contrato):
    contexto: Contexto
    registros: List[Dict[str, Any]]


class VariablesSalida(Contrato):
    feature_set_id: str
    features: List[Dict[str, float]]
    nombres: List[str]


# 5. Modelamiento
class ModeladoEntrada(Contrato):
    contexto: Contexto
    features: List[Dict[str, float]]


class ModeladoSalida(Contrato):
    modelo_id: str
    version_modelo: str
    metricas: Dict[str, float]
    variables: List[str]
    supera_baseline: bool = True


# 6. Validación
class ValidacionEntrada(Contrato):
    contexto: Contexto
    modelo_id: str
    version_modelo: str
    metricas: Dict[str, float]
    variables: List[str]
    supera_baseline: bool


class ValidacionSalida(Contrato):
    aprobado: bool
    veredicto: str
    motivos: List[str] = Field(default_factory=list)


# Servicio Inferencia
class InferenciaEntrada(Contrato):
    contexto: Contexto
    modelo_id: str
    variables_modelo: List[str]
    features: List[Dict[str, float]]


class InferenciaSalida(Contrato):
    riesgo: List[float]
    shap: List[Dict[str, float]]


# 7. Interpretación
class InterpretacionEntrada(Contrato):
    contexto: Contexto
    riesgo: List[float]
    shap: List[Dict[str, float]]


class InterpretacionSalida(Contrato):
    riesgo_max: float
    severidad: Severidad
    variables_influyentes: List[str]
    modo_falla: Optional[str] = None
    diagnostico: str


# 8. Recomendación
class RecomendacionEntrada(Contrato):
    contexto: Contexto
    severidad: Severidad
    modo_falla: Optional[str] = None
    variables_influyentes: List[str] = Field(default_factory=list)


class AccionPropuesta(BaseModel):
    id: str
    accion: str
    urgencia: str
    severidad: str
    estado_revision: str = "pendiente_especialista"


class RecomendacionSalida(Contrato):
    acciones: List[AccionPropuesta]


# 9. Monitoreo
class MonitoreoEntrada(Contrato):
    contexto: Contexto
    riesgo: List[float]
    acciones: List[AccionPropuesta] = Field(default_factory=list)


class MonitoreoSalida(Contrato):
    deriva_detectada: bool
    feedback: List[str] = Field(default_factory=list)


class RegistroAuditoria(Contrato):
    run_id: str
    agente: str
    estado: EstadoEjecucion
    inicio: datetime
    fin: datetime
    duracion_ms: float
    error: Optional[str] = None


class ResultadoFlujo(Contrato):
    run_id: str
    exito: bool
    salidas: Dict[str, Any] = Field(default_factory=dict)
    auditoria: List[RegistroAuditoria] = Field(default_factory=list)


def ahora() -> datetime:
    return datetime.now(timezone.utc)
