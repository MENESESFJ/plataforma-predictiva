# Agente 6: Validación y Gobierno

## Propósito
Actuar como un auditor ciego e independiente del modelo candidato. Busca activamente fallas, leakage o sobreajuste antes de solicitar la aprobación de paso a producción. Opera en el **Flujo de Entrenamiento**.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (Pruebas estadísticas automatizadas).
- **Uso de LLM:** Solo para formatear el informe final de auditoría.

## Responsabilidades
1. Pruebas de Data Leakage: verificar correlaciones espurias con variables administrativas.
2. Backtesting histórico por faena y estabilidad en el tiempo.
3. Comparar desempeño estricto contra el baseline del componente: si no lo supera, el modelo se rechaza.
4. Evaluar métricas de negocio: días de anticipación de alertas vs. tasa de falsas alarmas por mes.
5. Emitir veredicto para el Human-in-the-Loop (`aprobado_tecnicamente` / `rechazado`).
