# Servicio de Inferencia

## Propósito
Ejecutar el modelo activo y vigente sobre los datos actuales del equipo en el **Flujo de Inferencia**. No toma decisiones de orquestación, actúa como un motor de cómputo desacoplado.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (MLflow Model Flavor / ONNX / Pickle).
- **Uso de LLM:** Ninguno.

## Responsabilidades
1. Cargar el artefacto del modelo productivo registrado en MLflow.
2. Validar compatibilidad de firmas entre el `feature_set` y el modelo.
3. Calcular la probabilidad/riesgo de falla dentro del horizonte operativo.
4. Extraer explicabilidad local cuantitativa (valores SHAP por variable).
