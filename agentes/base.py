"""Clase base de agentes: auditoría, trazabilidad, errores y observabilidad."""
import logging
import time
from abc import ABC, abstractmethod
from typing import ClassVar, List, Optional, Type

from pydantic import BaseModel

from contratos.agentes import EstadoEjecucion, RegistroAuditoria, ahora


class ErrorAgente(Exception):
    def __init__(self, agente: str, causa: Exception):
        super().__init__(f"{agente}: {causa}")
        self.agente = agente
        self.causa = causa


class BaseAgente(ABC):
    nombre: ClassVar[str]
    entrada: ClassVar[Type[BaseModel]]
    salida: ClassVar[Type[BaseModel]]

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"agente.{self.nombre}")
        self.auditoria: List[RegistroAuditoria] = []

    @abstractmethod
    def procesar(self, datos):
        """Lógica del agente: recibe modelo de entrada, devuelve modelo de salida."""

    def ejecutar(self, datos, run_id: Optional[str] = None):
        run_id = run_id or getattr(getattr(datos, "contexto", None), "run_id", "n/a")
        if not isinstance(datos, self.entrada):
            datos = self.entrada.model_validate(datos)
        inicio, t0 = ahora(), time.perf_counter()
        error = None
        try:
            resultado = self.procesar(datos)
            if not isinstance(resultado, self.salida):
                resultado = self.salida.model_validate(resultado)
            self.logger.info("run=%s agente=%s ok", run_id, self.nombre)
            return resultado
        except Exception as exc:
            error = str(exc)
            self.logger.error("run=%s agente=%s error=%s", run_id, self.nombre, error)
            raise ErrorAgente(self.nombre, exc) from exc
        finally:
            self.auditoria.append(RegistroAuditoria(
                run_id=run_id, agente=self.nombre,
                estado=EstadoEjecucion.ERROR if error else EstadoEjecucion.OK,
                inicio=inicio, fin=ahora(),
                duracion_ms=(time.perf_counter() - t0) * 1000, error=error))
