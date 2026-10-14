# plataforma-predictiva
El proyecto tiene como objetivo desarrollar una Plataforma Agéntica de Analítica Predictiva para Confiabilidad y Mantenimiento, diseñada para transformar datos operacionales, de condición y mantenimiento en predicciones, explicaciones técnicas y recomendaciones accionables para la gestión de activos mineros.

## Estructura

```text
contratos/      # contratos Pydantic versionados (VERSION_CONTRATOS) y Estado global
agentes/        # BaseAgente, Supervisor y agentes (<agente>.py; README de diseño en <agente>/)
  tracer.py     # stubs de los agentes aún no productivos (Ingesta, Variables, Modelamiento, Validación, Monitoreo)
inferencia/     # Servicio de Inferencia (placeholder hasta Fase 3)
core/           # servicios compartidos: ConsultorSMCS y RegistroModelos (MLflow)
estado/         # persistencia del Estado global por request_id
trazabilidad/   # registro append-only de trazas por paso de agente
components/     # conocimiento por componente que lee el runtime: definición, reglas de calidad, FMEA aprobado, acciones y features
knowledge/
  smcs/         # matriz MF-SMCS y homologación FMEA↔SMCS
  fmea/         # FMEA del motor: fuentes de Confiabilidad, borrador, revisiones, decisiones y versión aprobada (ver su README)
herramientas/
  fmea/         # convertir_fmea.py (fuentes → borrador) y aplicar_revision.py (revisión → FMEA aprobado)
docs/
  fase0/        # Ficha de Caso de Uso (gate Fase 0)
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

Para registrar experimentos y modelos en MLflow (SQLite local por defecto, o `MLFLOW_TRACKING_URI`):

```python
from core.registro_modelos import RegistroModelos

registro = RegistroModelos("sqlite:///mlflow.db")
sup = Supervisor(registro=registro)
est = sup.ejecutar_solicitud(solicitud_entrenamiento, registros)   # registra la versión como "candidato"
registro.promover("motor_diesel", est.salidas["registro_modelo"]["version"])  # tras la aprobación humana
sup.ejecutar_solicitud(solicitud_inferencia, registros)            # usa el modelo "vigente"
```

Interfaz web: `mlflow ui --backend-store-uri sqlite:///mlflow.db`.

## Avance respecto del roadmap (Etapa 1)

| Fase | Estado |
|---|---|
| 0 Caso de uso | Piloto: DMH 798AC, 12 equipos, motor; 14 cambios de motor desde sep-2023 (9 imprevistos). Objetivo: detección de anomalías y degradación, horizonte de 15 días por validar. FMEA v1.0 aprobado, **aplicable** a DMH 798AC (DEC-001/002), aún no validado. Pendiente: listado validado de los 14 eventos, inventario de fuentes, métrica y firmas. Seguimiento en `docs/fase0/ficha_caso_uso_motor.md` |
| 1 Fundaciones | Contratos, Estado y trazas persistidos (SQLite), flujo reconstruible por `request_id`, CI, y MLflow para experimentos y registro de modelos (candidato → vigente con aprobación humana). Pendiente: entornos y secretos |
| 2 Datos y Calidad | Ingesta stub con hash determinístico; Calidad con score y veredicto (solo reglas de rango). Pendiente: fuentes, point-in-time, reglas temporales y las 22 variables que usa el FMEA, ya especificadas en `components/motor_diesel/data_contract.yaml` (hoy el catálogo de features tiene 5) |
| 3 Features/Modelo/Validación | Stubs |
| 4 Inferencia/Interpretación/Recomendación | Interpretación (con el FMEA aprobado y SMCS) y Recomendación por catálogo implementadas sobre una inferencia placeholder. Prompt LLM de Interpretación prototipado fuera del repo. En pausa hasta cerrar Fase 3 |
| 5–7 | Supervisor lineal con paso `human_in_the_loop`; resto pendiente |
