# Prueba 3: conclusiones de las primeras corridas (2026-11-24)

Agentes en secuencia (evidencia → fmea → revisor) con `gpt-5` en Azure AI Foundry, sobre tres cambios de
motor DMH 798AC. Corrieron con el razonamiento por defecto (medio), sin tope de tokens. Archivos:
`p3_caso_0_gpt-5.md`, `p3_caso_3_gpt-5.md`, `p3_caso_4_gpt-5.md`.

## Comparación con la clasificación manual

| Caso | Falla | Grupo manual | Modos del agente fmea | ¿Coincide? |
|---|---|---|---|---|
| 4 · MH344 2024 | Gripaje de metales de biela por contaminación vía filtro | lubricación y cojinetes (MFP-01 + MFP-07) | MFP-07, MFP-01 + **modo nuevo**: contaminación de la lubricación por traspaso interno del filtro | ✅ y agrega una propuesta |
| 3 · MH345 2024 | Bloqueo hidráulico por anillo cortafuego (UF 5) | bloqueo hidráulico, sin modo FMEA | MFP-07 (por el síntoma) + **modo nuevo**: bloqueo hidráulico | ✅ |
| 0 · MH341 2023 | Fatiga del engranaje loco de distribución | distribución delantera, sin modo FMEA | MFP-07 (por el síntoma) + **modo nuevo**: falla del tren de engranajes de distribución | ✅ |

**Resultado:** los 3 casos coinciden con la clasificación manual. En los dos grupos que el FMEA no cubre,
el agente pidió un modo nuevo por su cuenta. Eso respalda la propuesta a Confiabilidad de agregar esos modos.

## Modos nuevos propuestos por los agentes (para Confiabilidad)

1. **Bloqueo hidráulico por ingreso de fluido al cilindro** (anillo cortafuego, sello integral, fisura de camisa). Casos: MH345, MH348 y MH350.
2. **Falla del tren de engranajes de distribución delantera.** Casos: MH341 2023, MH344 2026 y, por tren de válvulas, MH352.
3. **Contaminación del sistema de lubricación por traspaso interno del filtro.** Caso: MH344 2024. A discutir: puede ser una causa de MFP-01 más que un modo nuevo.

## Lo que hicieron bien

- El agente de evidencia cita el registro sin interpretar y marca "no informado" cuando falta un dato.
- El revisor separa lo sustentado de lo supuesto. Marca como suposición las causas que el AFA dejó
  indeterminadas o en investigación del fabricante.
- Propone verificaciones útiles: Na/K y glicol en SOS para ingreso de refrigerante, la secuencia de alarmas
  en VIMS, rellenos para descartar bajo nivel, y el diferencial de presión del filtro (que sí existe como
  evento en el diccionario).

## Debilidades y ajustes aplicados

| Debilidad | Ajuste en `p3_analisis_secuencial.py` |
|---|---|
| Asigna MFP-07 en los tres casos solo por el síntoma "baja presión de aceite" | Instrucción del agente fmea: el síntoma no es el modo; los modos se asignan por causa y pieza |
| Pide verificar con Cat Inspect como si registrara desarmes, y en fechas en que no tenía datos (antes de jun-2026) | Instrucción del revisor: qué cubre cada fuente y desde cuándo; los hallazgos de desarme vienen del AFA/RCA o del informe de taller |
| No ve repeticiones en la flota (MH345 y MH348 comparten la causa "anillo cortafuego") | Pendiente: un agente con acceso al listado de eventos (patrón concurrente o de traspaso) |

## Segunda corrida: repetibilidad (mismas instrucciones, 2026-11-24)

Se repitieron los tres casos con las **mismas instrucciones** (el ajuste de arriba aún no estaba en main).
La primera corrida está en el historial de git (commit f7f91ee); la segunda y la tercera están copiadas en
`tests/fixtures/p3_eco/`.

| Caso | Agente fmea | Revisor | Similitud con el agente anterior |
|---|---|---|---|
| 0 · MH341 2023 | Igual que la primera: MFP-07 por el síntoma + modo nuevo de tren de distribución | Revisó bien; además cuestionó crear un modo nuevo sin revisar un catálogo FMEA más amplio | 0,19 / 0,17 (normal) |
| 3 · MH345 2024 | Igual que la primera: MFP-07 + modo nuevo de bloqueo hidráulico | **Parafraseó al agente fmea** en vez de revisar | 0,14 / **0,84** |
| 4 · MH344 2024 | **Copió textual la salida del agente de evidencia**; no asignó modos | **Copió textual la evidencia** | **1,00 / 1,00** |

**Hallazgo:** el flujo secuencial no es estable. En 2 de 3 casos, al menos un agente repitió al anterior en
vez de cumplir su rol (eco), y el resultado del caso 4 quedó sin análisis. En la primera corrida no pasó. Es
un riesgo propio de encadenar agentes que comparten la conversación, y debe controlarse antes de cualquier
uso real.

**Controles agregados en `p3_analisis_secuencial.py`:**
- Instrucción explícita a fmea y revisor de no repetir al agente anterior.
- Detección de eco: si la respuesta de un agente se parece en 70 % o más a la del anterior (lo normal es
  menos de 20 %), el flujo se repite, hasta 3 veces. Si persiste, el resultado queda marcado con una advertencia.
- Cada resultado registra el razonamiento usado, el máximo de tokens y el número de corridas.
- Test que reproduce la detección con los resultados reales de esta corrida.

**Lección para la arquitectura:** cada agente debería entregar una **salida estructurada** (contrato
Pydantic, como en la prueba 2). Con texto libre, una copia pasa como respuesta válida; con un formato fijo, se
detecta y se rechaza. Es la misma regla de `docs/arquitectura/patrones_orquestacion.md`.

## Tercera corrida (2026-11-24, sin detección de eco)

Corrió antes de que estuviera disponible la detección de eco. Las salidas siguen asignando MFP-07 por el
síntoma y el revisor no menciona Argos ni el AFA, por lo que probablemente usó las instrucciones anteriores.

| Caso | Agente fmea | Revisor | Similitud con el agente anterior |
|---|---|---|---|
| 0 · MH341 2023 | MFP-07 + modo nuevo de tren de distribución (igual que antes) | Revisó bien | 0,10 / 0,07 |
| 3 · MH345 2024 | **Copió textual la evidencia**; no asignó modos | Revisó bien, pero sobre la evidencia, sin análisis FMEA | **1,00** / 0,08 |
| 4 · MH344 2024 | MFP-07, MFP-01 + modo nuevo de contaminación por el filtro (igual que la primera) | Revisó bien | 0,23 / 0,16 |

**Balance de tres corridas con las mismas instrucciones:**
- En 9 corridas de caso hubo eco en 3: corrida 2 casos 3 y 4, corrida 3 caso 3. El caso que falla cambia de una corrida a otra.
- Cuando no hay eco, la clasificación es estable: el mismo modo nuevo en cada caso y la misma asignación de MFP-01 en el caso 4.
- La detección de eco de este PR habría marcado y repetido los 3 casos con problema.

## Cuarta corrida (2026-11-24, sin detección de eco)

Tampoco incluye las instrucciones ajustadas: sigue asignando MFP-07 por el síntoma, y el revisor propone
Cat Inspect para desarmes sin mencionar Argos ni el AFA. Probablemente la VM no tenía el código actualizado
(`git pull`).

| Caso | Agente fmea | Similitud con el agente anterior |
|---|---|---|
| 0 · MH341 2023 | MFP-07 + modo nuevo de tren de distribución | 0,18 / 0,05 |
| 3 · MH345 2024 | MFP-07 + modo nuevo de bloqueo hidráulico | 0,32 / 0,13 |
| 4 · MH344 2024 | MFP-07, MFP-01 + modo nuevo de contaminación por falla de filtración | 0,14 / 0,11 |

Sin eco. **Balance de cuatro corridas:** 3 ecos en 12 análisis de caso (25 %). Cuando no hay eco, la
clasificación se repitió igual en todas las corridas: los mismos modos y los mismos modos nuevos por caso.

## Quinta corrida (código anterior)

La VM no se había actualizado: el `git pull` se cancelaba porque los resultados locales tenían el mismo
nombre que los subidos por la web. En el caso 0, fmea y revisor copiaron textual la evidencia (eco).
**Balance de las corridas con el código anterior: 4 ecos en 15 análisis de caso.**

## Sexta corrida: primera con la versión nueva (instrucciones ajustadas + detección de eco)

Razonamiento medio, máximo de 8.000 tokens. Los tres casos se resolvieron en **1 corrida, sin eco**
(similitud con el agente anterior de 0,04 a 0,18).

| Caso | Agente fmea | Cambio respecto de las corridas anteriores |
|---|---|---|
| 0 · MH341 2023 | Ningún modo vigente aplica; MFP-07 **solo como consecuencia**; modo nuevo de tren de distribución | ✅ Ya no asigna MFP-07 como modo |
| 3 · MH345 2024 | **MFP-08 (combustión deficiente)** por la pérdida de sellado del anillo cortafuego; baja presión como consecuencia; modo nuevo de estanqueidad de junta con bloqueo hidráulico | ✅ Sin MFP-07. ⚠️ MFP-08 es nuevo y discutible (ver abajo) |
| 4 · MH344 2024 | **Solo MFP-01**; dice explícitamente "no asignar MFP-07: es el síntoma"; modo nuevo de contaminación por el filtro | ✅ Coincide con la causa, sin el síntoma |

**El revisor mejoró en los tres casos:**
- Pide los hallazgos de desarme solo al AFA/RCA o al informe de taller, ya no a Cat Inspect.
- Usa el particulado de rutina en Argos o Cat Inspect según corresponda.
- Distingue la consecuencia (baja presión) de la causa.
- En el caso 3 propone revisar la recurrencia en la flota y los boletines del fabricante.

**Para Confiabilidad, caso 3 y MFP-08:** el agente relacionó la pérdida de sellado del anillo cortafuego
con combustión deficiente. No es el modo de la falla (fue un bloqueo hidráulico por ingreso de fluido), pero
sugiere que las **señales de MFP-08 (temperatura de escape y su diferencial entre cilindros) podrían ser
precursoras** del modo nuevo de bloqueo hidráulico. Es una hipótesis a validar con los datos de VIMS de
MH345, MH348 y MH350.

**Conclusión:** las instrucciones ajustadas corrigieron los dos defectos de las corridas anteriores
(MFP-07 asignado por el síntoma y el mal uso de Cat Inspect), y la detección de eco no tuvo que actuar. Con
una sola corrida no se puede medir la tasa de eco con la instrucción de no repetir; conviene repetir 2 o 3
veces antes de concluir.

## Séptima corrida (versión nueva, repetición)

Los tres casos en 1 corrida, sin eco detectado con el umbral de entonces (0,7).

| Caso | Agente fmea | Revisor |
|---|---|---|
| 0 · MH341 2023 | Ningún modo vigente; MFP-07 descartado como modo; modo nuevo de tren de distribución | ✅ Revisó |
| 3 · MH345 2024 | **Ningún modo vigente** (esta vez sin MFP-08); MFP-07 descartado; modo nuevo de bloqueo hidráulico | ✅ Revisó; propone identificar el fluido con Na/K y rellenos |
| 4 · MH344 2024 | Solo MFP-01; MFP-07 descartado; analiza y descarta MFP-04; modo nuevo de contaminación por falla de filtración | ⚠️ **Parafraseó al fmea** (similitud 0,63): no separó lo supuesto ni nombró fuentes |

**Agente fmea, dos corridas con la versión nueva:** en 6 de 6 casos descartó MFP-07 como modo y propuso
el mismo modo nuevo por caso. Lo único que varió fue MFP-08 en el caso 3, que apareció en una corrida y no
en la otra. Su señal (temperatura de escape) sigue como hipótesis de precursor.

**Ajuste de la detección:** la paráfrasis del caso 4 pasó bajo el umbral de 0,7. Se baja a **0,5** (lo
normal fue hasta 0,32) y se agrega un **control de rol del revisor**: debe separar lo supuesto y nombrar al
menos una fuente para verificar. Con esto, las 13 corridas de caso archivadas en `tests/fixtures/p3_eco/`
quedan clasificadas como se revisaron a mano.

**Balance de la versión nueva:** 1 falla de rol en 6 análisis de caso. Las instrucciones de no repetir
redujeron las copias textuales (ninguna en 6), pero el revisor todavía puede limitarse a resumir. Es otro
argumento para la salida estructurada: un campo obligatorio de "supuestos" con su fuente lo haría verificable.

## Próximos pasos

1. Pasar a salida estructurada por agente (contratos Pydantic), como en la prueba 2: el revisor con campos obligatorios de lo sustentado, lo supuesto y la fuente de verificación.
2. Opcional: probar `--esfuerzo low` contra `medium` en el caso 4. Con 200.000 TPM no hace falta ahorrar; solo sirve si la cuota baja.
3. Correr la prueba 2 (los 14 casos, 3 repeticiones), si está permitido enviar el texto técnico.
