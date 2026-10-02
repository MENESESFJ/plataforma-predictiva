# Agente 4: Ingeniería de Variables (Features)

## Propósito
Transformar los datos crudos validados en variables analíticas reproducibles (condición, degradación, tendencias y ratios físicos) compartiendo el mismo pipeline en entrenamiento e inferencia.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (Python / Pandas / NumPy).
- **Uso de LLM:** Ninguno.

## Responsabilidades
1. Ejecutar el pipeline de transformaciones específico del componente (`feature_pipeline.py`).
2. Calcular variables de degradación (pendientes móviles, aceleraciones, deltas post-mantenimiento).
3. Asegurar ausencia total de data leakage mediante ventanas móviles causales hacia atrás.
4. Generar el identificador versionado del feature set (`feature_set_id`).

## Interacción con el SET del Componente
- Consume: `components/<componente_id>/feature_pipeline.py`.
