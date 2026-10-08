from __future__ import annotations

from datetime import date

from contratos.agentes import Contrato
from contratos.base import TipoFlujo


class SupervisorInput(Contrato):
    request_id: str
    caso_uso_id: str
    equipo: str
    tipo_flujo: TipoFlujo
    fecha_corte: date
    componente: str = "motor_diesel"
    ruta_componentes: str = "components"
