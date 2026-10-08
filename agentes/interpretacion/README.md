# Agente 7: Interpretación Técnica

## Propósito
Traducir la predicción matemática y los factores SHAP en una explicación física e ingenieril del deterioro del equipo, basada en el conocimiento de modos de falla del activo.

## Tipo de Componente
- **Naturaleza:** Razonamiento estructurado asistido por LLM.
- **Uso de LLM:** Sí (con entrada estructurada y prompt versionado).

## Responsabilidades
1. Recibir exclusivamente datos cuantitativos (riesgo, factores SHAP, tendencias).
2. Cruzar los síntomas con el catálogo de modos de falla del componente (`fmea.json`).
3. Generar una narrativa técnica donde cada afirmación esté respaldada por evidencia en las variables.
4. Identificar el modo de falla más probable según la matriz FMEA.

## Restricciones Operativas
- **No puede** modificar la probabilidad ni el nivel de riesgo emitido por el modelo.
- **No puede** emitir diagnósticos sin correlato en las variables entregadas.

## Interacción con el SET del Componente
- Consume: `components/<componente_id>/fmea.json`.
