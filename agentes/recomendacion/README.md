# Agente 8: Recomendación Operacional

## Propósito
Convertir el diagnóstico técnico en una acción de mantenimiento preventiva o correctiva acotada a las opciones autorizadas por la faena.

## Tipo de Componente
- **Naturaleza:** Motor de decisión determinístico asistido por LLM.
- **Uso de LLM:** Sí, estrictamente restringido al catálogo.

## Responsabilidades
1. Tomar el diagnóstico del Agente de Interpretación y el nivel de riesgo.
2. Consultar el catálogo de intervenciones habilitadas en el SET (`action_catalog.json`).
3. Asignar el nivel de urgencia operacional (ej. 24h, 72h, próximo mantenimiento programado).
4. Marcar la recomendación con estado `pendiente_especialista` para revisión humana obligatoria.

## Restricciones Operativas
- Prohibido generar acciones fuera de catálogo sin bandera de excepción.
- No emite órdenes de trabajo en ERP directamente: requiere validación humana.

## Interacción con el SET del Componente
- Consume: `components/<componente_id>/action_catalog.json`.
