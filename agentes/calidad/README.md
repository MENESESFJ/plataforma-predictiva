# Agente 3: Calidad de Datos

## Propósito
Auditar técnicamente el snapshot generado antes de permitir transformaciones o inferencias. Actúa como gate de contención determinístico.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (Pandera / Great Expectations).
- **Uso de LLM:** Opcional (solo redacción de observaciones secundarias para humanos).

## Responsabilidades
1. Evaluar las reglas de integridad física y operacional cargadas desde el SET del componente:
   - Monotonía y consistencia de horómetros/odómetros.
   - Rangos físicos admisibles (temperaturas, presiones, ppm de desgaste).
   - Cobertura temporal y completitud de variables clave.
2. Calcular score global de calidad (0 a 100).
3. Determinar el veredicto:
   - `aprobado` (score >= umbral).
   - `aprobado_con_observaciones`.
   - `rechazado` (detiene inmediatamente el flujo del Supervisor).

## Interacción con el SET del Componente
- Consume: `components/<componente_id>/quality_rules.yaml`.
