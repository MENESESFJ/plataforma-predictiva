# Plataforma predictiva de motor: avance para los equipos técnicos

Piloto DMH · CAEX 798AC · motor. Avance a noviembre de 2026.
Para Ingeniería, Monitoreo de Condiciones, Asesoría Técnica y Centro Técnico.

Presentación (15 diapositivas, descargable en PowerPoint o PDF): https://claude.ai/artifact/6ekqc7DhVcnppK3GJ82YeP
Este documento tiene el mismo contenido en texto.

---

## En una frase

**Una alerta temprana por camión que dice qué le pasa al motor, por qué lo creemos y qué revisar, antes de que la baja presión de aceite avise que ya es tarde.**

Lo que entrega: (1) qué camión muestra una condición anormal, desde cuándo y qué tan grave; (2) qué modo de falla del FMEA es compatible; (3) con qué evidencia, separando lo probado de lo supuesto; (4) qué revisar, como sugerencia que decide el especialista.

Por qué importa: 8 de las 10 fallas imprevistas desde 2023 se detectaron por baja presión de aceite, cuando el daño ya estaba hecho.

## 1. El objetivo

**Avisar antes de que el motor falle, y explicar por qué.**

- **Detectar:** encontrar condiciones anormales del motor con anticipación, juntando lo que hoy se mira por separado (VIMS, aceite, particulado y rellenos).
- **Explicar:** asociar cada alerta a los modos de falla del FMEA, con la evidencia que la respalda.
- **Apoyar, no reemplazar:** la plataforma propone; el especialista revisa y decide. Lo que el especialista corrige vuelve a la plataforma.

Piloto: contrato DMH · 14 camiones CAEX 798AC (MH340 a MH353) · componente motor · 14 cambios de motor desde septiembre de 2023.

## 2. Cómo funciona, en una sola imagen

```
ENTRA                         LA CAJA                                  SALE
Monitoreo VIMS        ┐   1. Ordena y limpia los datos           ┌ Alerta por camión
Análisis de aceite    │   2. Detecta anomalías: cuántas veces,   │ Modo de falla compatible
Particulado           ├─►    cuán severas y cuánto duran       ─►├ Qué revisar (decide el especialista)
Rellenos              │   3. Las compara con el FMEA             │ Tablero Power BI
Cambios de motor      ┘   4. Propone una explicación             └
                          Se alimenta de: FMEA del motor · historia de fallas ·
                          reglas para no usar datos "del futuro" · criterio de especialistas
```

## Quién hace qué

| | Qué hace | Cuándo y sobre qué |
|---|---|---|
| **Modelo numérico (sin IA)** | Lee VIMS, aceite, particulado y rellenos y busca desviaciones: (1) contra los límites que se usan hoy; (2) contra la historia del mismo camión, en la misma condición de operación; (3) contra camiones iguales ese día; (4) en tendencia, aunque no pase el límite. Entrega un estado por camión: normal, en observación, alerta o sin datos | Todos los días, todos los camiones, de forma automática |
| **IA (agentes)** | Arma el caso: modo de falla compatible, evidencia y qué revisar. No calcula ni decide alertas | Solo camiones en alerta nueva o que empeoró |
| **Especialista** | Revisa los casos y decide: inspeccionar, seguir o descartar. Valida qué desviaciones son reales y ayuda a ajustar los umbrales | Reunión semanal |

Un camión que no descarga datos queda **sin datos**, no pasa por sano. Estado: diseñado (`docs/arquitectura/monitor_desviaciones.md`) y por construir. Será el **primer entregable** (DP-006): Monitoreo de Condiciones tiene herramientas visuales para revisar un camión, pero no capacidad para mirar 150–180 cada día. El monitor revisa todos y les dice cuáles mirar, en qué parámetro y desde cuándo. Al comparar cada camión con su historia y con la flota, no necesita límites previos.

## 3. Entradas: qué información usa y en qué estado está

| Fuente | Qué aporta | Disponibilidad | Estado |
|---|---|---|---|
| Monitoreo VIMS | Presión de aceite, temperaturas, alarmas | ~12 descargas por camión al día | Ubicada y mapeada |
| Análisis de aceite | Fe, Cu, Pb, Si, Na/K, viscosidad, hollín | Desde 2022; se usa 3 días después de la muestra | Ubicada y mapeada |
| Particulado | Test de parche, rejillas, tapones | Argos hasta may-2026; Cat Inspect desde jun-2026 | Falta unir ambas |
| Rellenos | Litros de aceite y refrigerante | Por cada relleno | Ubicada y mapeada |
| Cambios y AFA/RCA | Qué falló y por qué | 14 cambios desde sep-2023 | Faltan 4 causas |

**Regla de oro:** cada análisis usa solo lo que se sabía en esa fecha. Los AFA/RCA sirven para aprender y validar, nunca para predecir, porque se escriben después de la falla.

## 4. Lo que alimenta la caja

- **FMEA del motor:** 8 modos de falla aprobados por Confiabilidad, cada uno con sus señales precursoras.
- **Historia de fallas:** los 14 cambios de motor, con modo de falla, causa raíz y pieza fallada cuando existen.
- **Reglas de uso de los datos:** solo lo que se sabía en cada fecha, solo la flota DMH y el motor, y Foresight antes que Argos.
- **Criterio de los especialistas:** revisión semanal de las alertas; lo que se confirma o corrige queda registrado.

## 5. Un caso real: MH344, diciembre de 2024

| Entra (registro del cambio) | La caja (tres agentes) | Sale |
|---|---|---|
| Cambio imprevisto a las 13.692 h | 1 · Evidencia: extrae solo los hechos | **Modo compatible: MFP-01**, desgaste de cojinetes |
| Síntoma: baja presión de aceite | 2 · FMEA: busca modos compatibles | **MFP-07 descartado:** la baja presión es el síntoma |
| Gripaje de metales de biela #19 y #20 | 3 · Revisor: separa lo probado de lo supuesto | **Propone un modo nuevo:** contaminación por falla del filtro |
| Contaminación por traspaso del filtro | | **Qué verificar:** Pb, Cu y Sn en aceite, alarma de diferencial del filtro, informe AFA |

Prueba hecha con agentes de IA en Azure sobre el registro escrito del cambio, repetida en varias corridas. Detalle en `experimentos/azure/resultados/conclusiones_p3.md`. Siguiente paso: hacerlo con los datos de condición de las semanas previas a la falla.

## 6. Lo que aprendimos de los 14 cambios de motor

- **10 + 4:** fallas imprevistas y cambios programados por PCR, desde septiembre de 2023.
- **8 de 10** fallas se detectaron por baja presión de aceite, con causas muy distintas detrás: **la baja presión es el aviso, no la causa.**
- **1 de 7** fallas con causa conocida calza bien en el FMEA actual.

| Grupo de falla real | Casos | ¿Está en el FMEA? |
|---|---|---|
| Distribución delantera | MH341 (2023), MH352, MH344 (2026) | No |
| Bloqueo hidráulico | MH345, MH348, MH350 | Solo en parte |
| Lubricación y cojinetes | MH344 (2024) + 2 sin causa | Sí: MFP-01 y MFP-07 |

**Propuesta para Confiabilidad:** agregar dos modos al FMEA, **bloqueo hidráulico** (ingreso de fluido al cilindro) y **tren de distribución** (engranajes y tren de válvulas). A discutir: contaminación por falla del filtro, ¿modo nuevo o causa de MFP-01? Hipótesis: la temperatura de escape por cilindro podría anticipar el bloqueo hidráulico.

## 7. Dónde estamos

| Etapa | Estado | Comentario |
|---|---|---|
| Definir el caso | Casi listo | Falta validación de Confiabilidad |
| Base técnica | Lista | Destino Microsoft Fabric y Azure ML |
| Datos | Definidos | Falta conectar los datos reales |
| Detección de anomalías | Diseñada | Monitor de desviaciones VIMS, por construir: primer entregable para Monitoreo de Condiciones |
| Agentes de IA | Probados | En Azure, 3 casos reales y 7 corridas |

## 8. Cómo se usará

Cada semana: **alerta → revisión técnica → decisión (inspeccionar, seguir o descartar) → registro.** Lo que el especialista confirma o descarta vuelve a la plataforma. Ninguna acción se ejecuta sin revisión humana.

## 9. Qué necesitamos de cada equipo (propuesta para conversar)

| Equipo | Qué necesitamos | Para qué |
|---|---|---|
| Ingeniería y Confiabilidad | Validar el modo de falla de los 14 cambios y decidir los 2 modos nuevos | Que la plataforma aprenda de fallas bien clasificadas |
| Monitoreo de Condiciones | Cuántos camiones pueden revisar por semana; revisar las primeras listas del monitor; rango y unidad de cada parámetro VIMS; si el amarillo de Cat Inspect ya es severo | Mirar solo los camiones que importan, no toda la flota |
| Centro Técnico | Causa raíz de 4 fallas sin registro (MH349, MH340, MH341 y MH344 de 2025–2026) e informes de desarme | Completar la historia de fallas |
| Asesoría Técnica | Revisar las primeras alertas; evaluar la temperatura de escape como señal previa del bloqueo hidráulico | Que la explicación sirva en terreno |

## 10. Corto plazo: cinco pasos para la primera alerta real

1. Validar los 14 cambios de motor y los 2 modos nuevos del FMEA.
2. Asegurar una copia del histórico de la flota DMH desde 2023 (Databricks se retira en 2027).
3. Construir el monitor de desviaciones VIMS, primer entregable para Monitoreo de Condiciones: revisa toda la flota a diario y entrega la lista corta de camiones a mirar; después se suman aceite, particulado y rellenos.
4. Probarla hacia atrás: ¿habría avisado antes de cada una de las 10 fallas, con cuánta anticipación y cuántas falsas alarmas?
5. Primera revisión semanal con especialistas y acordar la métrica de éxito.

## 11. Para conversar en la reunión

1. ¿Quién valida los modos de falla de los 14 cambios, y cuándo?
2. ¿Qué necesitan ver de VIMS cada día, y cuántas alertas por semana pueden revisar?
3. ¿Quién puede aportar las 4 causas raíz pendientes?
4. ¿Con qué frecuencia y en qué instancia revisamos casos juntos?
