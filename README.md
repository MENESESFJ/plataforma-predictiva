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
components/     # conocimiento por componente que lee el runtime: definición, reglas de calidad, FMEA aprobado, acciones y features
knowledge/
  smcs/         # matriz MF-SMCS y homologación FMEA↔SMCS
  fmea/         # FMEA del motor: fuentes de Confiabilidad, borrador, revisiones, decisiones y versión aprobada (ver su README)
herramientas/
  fmea/         # convertir_fmea.py (fuentes → borrador) y aplicar_revision.py (revisión → FMEA aprobado)
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
| 0 Caso de uso | FMEA del motor v1.0 aprobado por Confiabilidad (8 modos predictivos) y en uso; 798AC cubierto por equivalencia con 793F/797F (DEC-001). Pendiente: flota piloto, Ficha aprobada, eventos etiquetados, códigos OT (`definition.json` en `POR_CONFIRMAR`) y los puntos abiertos de `knowledge/fmea/README.md` |
| 1 Fundaciones | Contratos, Estado y trazas persistidos (SQLite), flujo reconstruible por `request_id`, CI. Pendiente: MLflow, entornos y secretos |
| 2 Datos y Calidad | Ingesta stub con hash determinístico; Calidad con score y veredicto (solo reglas de rango). Pendiente: fuentes, point-in-time, reglas temporales y las ~20 variables que usa el FMEA (hoy el catálogo tiene 5) |
| 3 Features/Modelo/Validación | Stubs |
| 4 Inferencia/Interpretación/Recomendación | Interpretación (con el FMEA aprobado y SMCS) y Recomendación por catálogo implementadas sobre una inferencia placeholder. Prompt LLM de Interpretación prototipado fuera del repo. En pausa hasta cerrar Fase 3 |
| 5–7 | Supervisor lineal con paso `human_in_the_loop`; resto pendiente |
