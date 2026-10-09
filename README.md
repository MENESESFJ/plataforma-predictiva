# plataforma-predictiva
El proyecto tiene como objetivo desarrollar una Plataforma Agéntica de Analítica Predictiva para Confiabilidad y Mantenimiento, diseñada para transformar datos operacionales, de condición y mantenimiento en predicciones, explicaciones técnicas y recomendaciones accionables para la gestión de activos mineros.

## Estructura

```text
contratos/      # contratos Pydantic versionados (VERSION_CONTRATOS) y Estado global
agentes/        # BaseAgente, Supervisor y agentes (<agente>.py; README de diseño en <agente>/)
  tracer.py     # stubs de los agentes aún no productivos (Ingesta, Variables, Modelamiento, Validación, Monitoreo)
inferencia/     # Servicio de Inferencia (placeholder hasta Fase 3)
core/           # servicios de dominio compartidos (ConsultorSMCS)
estado/         # persistencia del Estado global por request_id
trazabilidad/   # registro append-only de trazas por paso de agente
components/     # conocimiento por componente: definición, reglas de calidad, FMEA, catálogo de acciones y features
knowledge/      # conocimiento transversal (matriz MF-SMCS y homologación FMEA↔SMCS)
tests/
```

`components/<componente>/` cumple el rol de `config/` del roadmap: umbrales, reglas y catálogos se versionan como datos, no como código.

## Convención de identificadores

| Identificador | Origen | Formato |
|---|---|---|
| `request_id` | quien solicita el flujo (`SupervisorInput`) | libre, único; el Supervisor rechaza uno ya registrado |
| `run_id` | igual al `request_id` del flujo | se propaga en `Contexto` y en cada `RegistroAuditoria` |
| `dataset_id` | Agente Ingesta | `<componente>-<AAAAMMDD fecha_corte>-<sha256[:12] del snapshot>` |
| `feature_set_id` | Agente Variables | `<componente>-fs-<sha256[:12] de las features>` |

## Ejecución

```bash
pip install -r requirements.txt
pytest
```

Para persistir el Estado y las trazas:

```python
from agentes.supervisor import Supervisor
from estado import RepositorioEstado
from trazabilidad import RegistroTrazas

sup = Supervisor(repositorio=RepositorioEstado("plataforma.db"),
                 trazas=RegistroTrazas("plataforma.db"))
estado = sup.ejecutar_solicitud(solicitud, registros)
RepositorioEstado("plataforma.db").cargar(solicitud.request_id)  # reconstrucción
```

## Avance respecto del roadmap (Etapa 1)

| Fase | Estado |
|---|---|
| 0 Caso de uso | Pendiente fuera del repo: Ficha aprobada, eventos etiquetados, códigos OT (`definition.json` en `POR_CONFIRMAR`) |
| 1 Fundaciones | Contratos, Estado y trazas persistidos (SQLite), flujo reconstruible por `request_id`, CI. Pendiente: MLflow, entornos y secretos |
| 2 Datos y Calidad | Ingesta stub con hash determinístico; Calidad con score y veredicto (solo reglas de rango). Pendiente: fuentes, point-in-time, reglas temporales |
| 3 Features/Modelo/Validación | Stubs |
| 4 Inferencia/Interpretación/Recomendación | Interpretación FMEA+SMCS y Recomendación por catálogo implementadas sobre una inferencia placeholder. En pausa hasta cerrar Fase 3 |
| 5–7 | Supervisor lineal con paso `human_in_the_loop`; resto pendiente |
