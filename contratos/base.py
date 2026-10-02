"""Esquema del Estado global del flujo (persistido por el Supervisor)."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Dict, List

from pydantic import Field

from contratos.agentes import Contrato, RegistroAuditoria


class TipoFlujo(str, Enum):
    ENTRENAMIENTO = "entrenamiento"
    INFERENCIA = "inferencia"


class FaseFlujo(str, Enum):
    EN_CURSO = "en_curso"
    PENDIENTE_HUMANO = "pendiente_humano"
    FALLIDO = "fallido"


class Estado(Contrato):
    request_id: str
    caso_uso_id: str
    equipo: str
    componente: str
    tipo_flujo: TipoFlujo
    fecha_corte: date
    fase: FaseFlujo = FaseFlujo.EN_CURSO
    pasos_completados: List[str] = Field(default_factory=list)
    salidas: Dict[str, Any] = Field(default_factory=dict)
    auditoria: List[RegistroAuditoria] = Field(default_factory=list)
    errores: List[str] = Field(default_factory=list)
    cerrado: bool = False
