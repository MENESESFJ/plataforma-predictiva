# Agente 5: Modelamiento Predictivo

## Propósito
Entrenar y registrar modelos matemáticos (supervivencia, clasificación o regresión) orientados a anticipar la falla del componente superando el baseline establecido. Opera únicamente en el **Flujo de Entrenamiento**.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (Scikit-learn, XGBoost, Lifelines, Scikit-survival).
- **Uso de LLM:** Ninguno.

## Responsabilidades
1. Entrenar el baseline definido en el caso de uso (ej. Kaplan-Meier, Regresión Logística simple).
2. Entrenar modelos candidatos (Random Survival Forest, Cox, Gradient Boosting).
3. Implementar esquemas de validación temporal y agrupada por equipo (*GroupKFold* por ID de equipo).
4. Manejar censura y desbalance severo de clases.
5. Registrar métricas, artefactos e hiperparámetros en MLflow.

## Interacción con el SET del Componente
- Consume: `components/<componente_id>/definition.json` (baseline y evento objetivo).
