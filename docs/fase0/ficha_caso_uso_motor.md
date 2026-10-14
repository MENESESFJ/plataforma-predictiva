# Ficha de Caso de Uso – Motor CAEX 798AC, contrato DMH

| | |
|---|---|
| Versión | 0.2 (borrador) |
| Estado | En construcción – requiere firma de Confiabilidad y Data Analytics (gate Fase 0) |
| Tenant | Contrato **DMH** · modelo **798 AC** · componente `motor_diesel` |
| Roadmap | Etapa 1, Fase 0 |

Marcas: ✅ CONFIRMADO · 🟡 SUPUESTO DE DISEÑO / por validar · ⬜ POR_CONFIRMAR.

Principio: **el modelo detecta, el FMEA contextualiza, el especialista confirma.**

---

## 1. Alcance del piloto

| Campo | Valor | Estado |
|---|---|---|
| Contrato | DMH | ✅ |
| Modelo de equipo | CAEX 798AC (accionamiento eléctrico) | ✅ |
| Universo | 12 equipos | ✅ |
| Componente | Motor | ✅ |
| Unidad de análisis | Motor instalado en un equipo durante su ciclo de vida (instalación → retiro) | 🟡 |
| Historia disponible | ~3 años, desde el inicio de operación de DMH 798AC | ✅ aproximado |

## 2. Objetivos analíticos

| Objetivo | Descripción | Estado |
|---|---|---|
| Primario | Detectar tempranamente condiciones anormales del motor que justifiquen atención, seguimiento o intervención | ✅ |
| Secundario | Determinar si la condición anormal es consistente con degradación y, con evidencia suficiente, asociarla a modos FMEA posibles | ✅ |
| Forma de la salida | Compatibilidad o hipótesis respaldada por evidencia; nunca diagnóstico confirmado | ✅ |

Flujo conceptual: datos → calidad → features → detección de anomalía → persistencia/degradación → compatibilidad FMEA → interpretación → recomendación → validación humana → retroalimentación.

**Por qué detección de anomalías y no predicción de falla:** con 9 cambios imprevistos en ~3 años, un modelo supervisado de falla tendría muy poca base. Esto está alineado con la mitigación del roadmap para "pocos eventos" (objetivo intermedio).

## 3. Eventos históricos (ground truth)

| Campo | Valor | Estado |
|---|---|---|
| Cambios de motor desde sep-2023 | 14 | ✅ informado |
| Imprevistos | 9 | ✅ informado |
| Programados | 5, por condición detectada y/o PCR/TBO | ✅ informado |
| Datos por cambio | Fecha de instalación y de retiro, causa, equipo e historia del período | ✅ informado |
| Listado evento por evento | `docs/fase0/plantilla_eventos_motor.csv` | ⬜ completar con los 14 casos |
| Validación por Confiabilidad | Caso a caso | ⬜ |
| AFA / RCA | Disponibles en varios casos | ✅ informado · ⬜ cuáles |

**Regla:** AFA y RCA se generan después del evento. Sirven para etiquetar, validar resultados y contrastar con el FMEA. **Nunca son variables predictoras** (regla en el contrato de datos, con test).

Ventanas de análisis por evento: T-90, T-60, T-30, T-15, T-7 y T0, donde T0 es el cambio de motor.

## 4. Horizonte

| Campo | Valor | Estado |
|---|---|---|
| Horizonte operacional | 15 días | 🟡 Hipótesis: se valida empíricamente con las ventanas de los 14 eventos |
| Valor anterior (descartado) | 30 días / 250 h | — |

## 5. Baseline (práctica actual)

| Campo | Valor | Estado |
|---|---|---|
| Práctica actual | Reemplazo a las 16.000 h, ajustado por factor de carga (memoria RCM, RCM-002) | ✅ |
| Baseline estadístico | Kaplan-Meier, solo descriptivo (14 eventos) | 🟡 |
| Baselines de anomalía | Individual por motor y poblacional DMH 798AC, aprendidos del histórico | 🟡 |
| Umbrales de anomalía | **No se fijan a priori**; se calibran con el histórico | ✅ principio |

## 6. Métrica y restricciones

| Campo | Valor | Estado |
|---|---|---|
| Métrica principal | ⬜ Por ejemplo: cambios imprevistos con alerta persistente dentro del horizonte | ⬜ |
| Falsas alarmas tolerables | ⬜ Por equipo-mes, con capacidad de la reunión semanal | ⬜ |
| Expectativas | Con 14 eventos se reportan casos e intervalos, no porcentajes de precisión | 🟡 |

## 7. Conocimiento FMEA

| Campo | Valor | Estado |
|---|---|---|
| FMEA del motor | v1.0, 8 modos predictivos aprobados por Confiabilidad | ✅ |
| Nivel para DMH 798AC | **APLICABLE** en los 8 modos (DEC-001 y DEC-002): similitud técnica con 793F/797F | ✅ |
| Nivel VALIDADO para DMH 798AC | Ningún modo todavía; requiere contraste con los 14 cambios y sus AFA/RCA | ⬜ |
| Feature importance previa (otros motores) | No se reutiliza como ponderación ni como conocimiento experto; si se usa, se recalcula con datos DMH 798AC | ✅ principio |

## 8. Plataforma y restricciones

| Campo | Valor | Estado |
|---|---|---|
| Procesamiento | Databricks con Python | ✅ |
| Acceso a datos | Solo lectura sobre Bronze/Silver; datasets derivados propios | ✅ |
| Pipelines y orquestador corporativo | No se modifican | ✅ |
| Persistencia de resultados | SQL Server y/o Data Lake | ⬜ cuál y dónde |
| Registro de modelos | MLflow (el que ya trae Databricks) | 🟡 |
| Visualización | Power BI; no es la fuente de verdad | ✅ |
| LLM | Ninguna dependencia obligatoria; posible Azure AI Foundry/OpenAI desde ene-2027, detrás de una interfaz desacoplada | ✅ |
| Revisión humana | Reunión técnica semanal con especialistas, con registro estructurado | ✅ |

## 9. Inventario de fuentes — por validar

Detalle técnico en `components/motor_diesel/data_contract.yaml`. Las familias vienen de la descripción del proyecto y se consideran **posiblemente válidas hasta confirmarlas**.

| Fuente en el contrato | Familias candidatas | Validado | Responsable de acceso |
|---|---|---|---|
| Análisis de aceite | SOS / APD | ⬜ | ⬜ |
| Particulado | Inspecciones de particulado, Cat Inspect | ⬜ | ⬜ |
| Monitoreo del equipo | VIMS eventos y tendencias | ⬜ | ⬜ |
| Mantenimiento | Mantenimiento, fallas de componentes, SMCS | ⬜ | ⬜ |
| Horas | Horas del equipo | ⬜ | ⬜ |
| Ciclo de vida del motor | Fecha de instalación de componentes | ⬜ | ⬜ |
| Rellenos | Rellenos | ⬜ | ⬜ |
| Detenciones | Detenciones | ⬜ | ⬜ |
| Operación | Variables operacionales | ⬜ | ⬜ |
| AFA / RCA (solo etiqueta) | AFA, RCA | ⬜ | ⬜ |
| **Sin asignar** | Foresight, Argos / Argos Clone, AMT, API CAT | ⬜ | ⬜ |

## 10. Validaciones pendientes con el responsable del proyecto

1. **Familias sin asignar:** qué contiene cada una de Foresight, Argos/Argos Clone, AMT y API CAT, y si duplican o complementan a VIMS, SOS o mantenimiento.
2. **Cat Inspect:** ¿corresponde a inspecciones de particulado, a inspecciones visuales, o a ambas?
3. **SOS / APD:** ¿son la misma fuente o dos? ¿En la tabla queda registrada la fecha de informe además de la de muestra? Es la regla que evita leakage.
4. **VIMS:** ¿hay tendencias resumidas, eventos, o ambos? ¿Con qué frecuencia y desde cuándo hay datos para los 12 equipos?
5. **Cambios de motor:** ¿dónde está el listado de los 14 cambios? ¿Los AFA/RCA están digitalizados y con fecha de emisión?
6. **Persistencia:** ¿los resultados del MVP van a SQL Server, al Data Lake, o a ambos? ¿Qué lee Power BI hoy?

## 11. Riesgos específicos del caso

| Riesgo | Mitigación |
|---|---|
| Solo 9 cambios imprevistos | Detección de anomalías + degradación; validación caso a caso; intervalos, no porcentajes |
| Leakage por AFA/RCA o por fecha de muestra SOS | AFA/RCA prohibidos como predictor; SOS se corta por fecha de informe (ambos con regla en el contrato) |
| Umbrales arbitrarios | Calibración con el histórico, baseline individual y poblacional |
| Sobreinterpretación del FMEA | Salida como compatibilidad; niveles propuesto → aplicable → validado |
| Duty cycle del accionamiento eléctrico | Baseline propio de DMH 798AC; no extrapolar desde otras flotas o faenas |

## 12. Aprobación (gate Fase 0)

| Rol | Nombre | Fecha | Firma |
|---|---|---|---|
| Confiabilidad | | | |
| Data Analytics | | | |
| Líder de proyecto | | | |

Criterio de salida: ficha firmada, listado de los 14 eventos validado por especialista y accesos a las fuentes principales otorgados o con fecha comprometida.
