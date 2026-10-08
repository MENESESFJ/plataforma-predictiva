"""Contratos Pydantic versionados de entrada/salida para los nueve agentes."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

VERSION_CONTRATOS = "1.0.0"


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


class Contexto(Contrato):
    """Contexto compartido del flujo analítico."""
    run_id: str
    componente: str
    ruta_componentes: str = "components"


# 2. Ingesta
class IngestaEntrada(Contrato):
    contexto: Contexto
    registros: List[Dict[str, Any]]


class IngestaSalida(Contrato):
    registros: List[Dict[str, Any]]
    n_registros: int


# 3. Calidad
class CalidadEntrada(Contrato):
    contexto: Contexto
    registros: List[Dict[str, Any]]


class CalidadSalida(Contrato):
    registros_validos: List[Dict[str, Any]]
    n_rechazados: int
    violaciones: List[str] = Field(default_factory=list)


# 4. Ingeniería de variables
class VariablesEntrada(Contrato):
    contexto: Contexto
    registros: List[Dict[str, Any]]


class VariablesSalida(Contrato):
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


# 6. Validación y gobierno
class ValidacionEntrada(Contrato):
    contexto: Contexto
    modelo_id: str
    version_modelo: str
    metricas: Dict[str, float]
    variables: List[str]


class ValidacionSalida(Contrato):
    aprobado: bool
    motivos: List[str] = Field(default_factory=list)


# Servicio de inferencia (determinístico)
class InferenciaEntrada(Contrato):
    contexto: Contexto
    modelo_id: str
    variables_modelo: List[str]
    features: List[Dict[str, float]]


class InferenciaSalida(Contrato):
    riesgo: List[float]
    shap: List[Dict[str, float]]


# 7. Interpretación técnica
class InterpretacionEntrada(Contrato):
    contexto: Contexto
    riesgo: List[float]
    shap: List[Dict[str, float]]


class InterpretacionSalida(Contrato):
    riesgo_max: float
    severidad: Severidad
    variables_influyentes: List[str]
    modo_falla: Optional[str] = None


# 8. Recomendación operacional
class RecomendacionEntrada(Contrato):
    contexto: Contexto
    severidad: Severidad
    modo_falla: Optional[str] = None


class RecomendacionSalida(Contrato):
    acciones: List[str]


# 9. Monitoreo y retroalimentación
class MonitoreoEntrada(Contrato):
    contexto: Contexto
    riesgo: List[float]
    acciones: List[str]


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
