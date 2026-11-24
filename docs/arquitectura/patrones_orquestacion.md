# Patrones de orquestación de agentes: qué usar en cada parte

Propuesta para el piloto DMH 798AC (motor) y su evolución hacia Azure (Microsoft Agent Framework con
agentes de Azure AI Foundry, previsto para 2027). Plataforma de datos y modelos: Microsoft Fabric y
Azure Machine Learning (DP-005).

**Principio:** no se elige un patrón para todo. Lo productivo y auditable va en un flujo secuencial y
determinístico; los patrones con más autonomía se reservan para tareas de análisis revisadas por una
persona. Se mantiene el orden del roadmap: primero el pipeline determinístico, luego los agentes con LLM,
al final la orquestación inteligente.

## Resumen

| Patrón | Uso en el proyecto | Cuándo |
|---|---|---|
| **Secuencial** | Pipeline diario: ingesta → calidad → anomalías y variables → modelo → interpretación → recomendación | Ya existe (`agentes/supervisor.py`) |
| **Concurrente** | Buscar evidencia en SOS, Cat Inspect y AFA/RCA en paralelo para un caso | Con LLM (2027) |
| **Traspaso (handoff)** | Triage del caso y derivación al especialista por grupo de falla | Triage por reglas antes de 2027; especialistas con LLM en 2027 |
| **Chat grupal** | Casos raros en que dos especialistas no coinciden | Excepción |
| **Magentic** | Investigar fallas sin causa raíz, a pedido | Herramienta de análisis, nunca en producción |

## 1. Secuencial: el pipeline productivo

```
Ingesta → Calidad → Anomalías/variables → Modelo → Validación → MLflow (candidato)      [entrenamiento]
Ingesta → Calidad → Anomalías/variables → Inferencia → Interpretación → Recomendación   [inferencia]
```

- Mismo orden y mismo resultado con los mismos datos; estado persistido después de cada paso; traza por agente.
- Sin LLM en el cálculo: anomalías, scores y reglas de corte son código (DP-003).
- Es lo que exige un proceso auditable de mantenimiento.

## 2. Traspaso: análisis de cada caso con anomalía

```
Entrada: caso con anomalías (variable + dirección), del pipeline
        │
  Triage del caso ── decide por la firma de anomalías
        │
  ├─ Lubricación y cojinetes            (MFP-01, MFP-07)
  ├─ Ingreso de fluido / refrigerante   (MFP-03, MFP-06 + modo nuevo propuesto)
  ├─ Distribución y desgaste            (modo nuevo propuesto, MFP-02, MFP-04)
  ├─ Combustión                         (MFP-05, MFP-08)
  └─ Sin firma clara                    → especialista humano
        │
  Cada especialista: evidencia citada + modo compatible + confianza (contrato de Interpretación)
        │
  Humano (Confiabilidad) valida → reunión semanal
```

Los grupos vienen de los 14 cambios de motor reales (`docs/fase0/eventos_motor_dmh_798_borrador.csv`).

Condiciones:
1. El triage decide primero por reglas (firma de anomalías vs señales del FMEA); el LLM solo para firmas ambiguas.
2. Máximo 2 traspasos por caso; después, al humano.
3. Salida estructurada obligatoria; nada en texto libre.

Encaje con el código actual: el agente de Interpretación se divide en triage + especialistas; su cruce
variables ↔ modos FMEA pasa a ser la regla del triage.

## 3. Concurrente: evidencia en paralelo

Dentro de un especialista, la búsqueda de evidencia en SOS, Cat Inspect y AFA/RCA puede correr en
paralelo y unirse al final. Reduce tiempo, no cambia el resultado.

## 4. Chat grupal: solo como excepción

Los agentes comparten una conversación y un administrador decide quién habla. Sirve para lluvia de ideas
y síntesis, no para un proceso repetible. Uso propuesto: casos en que dos especialistas proponen modos
distintos, con límite de rondas, salida estructurada y el humano en la conversación.

## 5. Magentic: investigación de casos sin causa, a pedido

Un orquestador arma un plan, elige qué agente actúa en cada vuelta y lo replantea si no avanza. Su
"libro de tareas" separa hechos verificados, hechos por comprobar y suposiciones fundamentadas, la misma
disciplina que el repositorio usa con CONFIRMADO / POR_CONFIRMAR / SUPUESTO.

Uso propuesto: reconstruir la historia de fallas sin causa registrada (hoy MH349 2025-04, MH340 2025-07,
MH341 2026-05 y MH344 2026-07).

Condiciones:
- Solo a pedido de una persona; nunca automático ni diario.
- Tope de vueltas y de costo por investigación.
- Solo lectura de datos y resultados ya calculados.
- El resultado es una hipótesis para Confiabilidad; entra al listado de eventos solo si un especialista la valida.

No se usa en producción: puede seguir caminos distintos con los mismos datos, entrar en bucles y tener
costo impredecible.

## Agentes actuales y su evolución

| Agente actual | Hoy | Evolución |
|---|---|---|
| Supervisor | Máquina de estados secuencial | Se mantiene; en Azure, flujo de pasos fijos de Agent Framework |
| Ingesta | Mínimo (registros en memoria) | Lee el lake o Fabric por ruta, con los filtros del contrato (Fase 2) |
| Calidad | Reglas de rango | Agrega reglas temporales y de corte (Fase 2) |
| Variables + Modelamiento | Mínimos | Detección de anomalías rearmada: veces, severidad, permanencia por fuente (Fase 3) |
| Validación | Mínimo | Contra los 14 eventos, caso a caso (Fase 3) |
| Inferencia | Implementado | Usa el modelo vigente desde Azure ML |
| Interpretación | Por probabilidad y SHAP | Triage + especialistas por grupo de falla (traspaso) |
| Recomendación | Por catálogo | Se mantiene; acciones siempre pendientes de especialista |
| Monitoreo | Mínimo, fuera de los flujos | Fase 7 |
| — (nuevo) | — | Registro estructurado del feedback de la revisión semanal |
| — (nuevo) | — | Investigación de casos sin causa (Magentic, a pedido) |

## Reglas comunes a todos los patrones con LLM

1. El LLM nunca calcula: lee resultados ya calculados mediante funciones.
2. Salida validada contra el contrato Pydantic; si no cumple, se rechaza.
3. Se activa solo en casos con algo que revisar, no en toda la flota cada día.
4. Cada conversación y traspaso se guarda como traza.
5. Evaluación contra casos revisados por especialistas antes de pasar a producción.
6. Los nombres de los servicios de Azure cambian seguido: confirmar nombres y disponibilidad en la región al definir la plataforma 2027.
