# Monitor de desviaciones (modelo numérico, sin IA)

Diseño detallado de la detección de anomalías del proyecto (DP-003). Desde DP-006 es además un **entregable propio
para Monitoreo de Condiciones**. Ese equipo tiene herramientas, básicamente visuales, para revisar un camión, pero no
tiene capacidad para revisar a diario los 150–180 equipos de la flota. El monitor revisa todos los camiones y les dice
**cuáles mirar, en qué parámetro y desde cuándo**, para que los revisen con sus herramientas de siempre.

Marcas: CONFIRMADO · PROPUESTA (decisión de diseño, revisable) · POR_CALIBRAR (valor que se fija con datos y con
Monitoreo de Condiciones). **Ningún umbral de este documento es definitivo:** los valores que aparecen son puntos de
partida para calibrar.

## 1. Para qué sirve

| Uso | Quién lo usa | Qué obtiene |
|---|---|---|
| **Monitor diario (revisión por excepción)** | Monitoreo de Condiciones | La lista corta de camiones que vale la pena mirar hoy: cuál, en qué parámetro, desde cuándo y cuánto se desvía de su historia y de la flota. El resto de la flota no requiere revisión |
| **Insumo del modelo predictivo** | La plataforma | Veces, severidad y permanencia de las desviaciones por fuente (el mismo patrón del modelo productivo actual) |
| **Disparador de la IA** | Agentes | Solo los camiones en alerta pasan a la interpretación |

El monitor tiene valor por sí solo, sin el modelo predictivo ni la IA. Por eso es el **primer entregable** (sección 10).

## 2. Alcance por etapas

| Etapa | Fuentes | Flota |
|---|---|---|
| **1** | VIMS: tendencias (`ds_Trends_798`) y eventos (`ds_EventDuration_798`), y análisis de aceite (SOS) | DMH 798AC (MH340–MH353) |
| 2 | + particulado (Argos y Cat Inspect) y rellenos | DMH 798AC |
| 3 | Las mismas | Otros contratos 798AC; luego 797B/F (150–180 equipos) |

## 3. Unidad de análisis

**Camión × motor instalado × parámetro × condición de operación × día.**

- **Condición de operación** (CONFIRMADO, viene en VIMS): por ejemplo "Engine Running, RPM High, Warm, Loaded". Un
  parámetro solo se compara dentro de la misma condición, para no confundir carga de trabajo con desgaste.
- **Motor instalado** (PROPUESTA): la historia de un camión se reinicia cuando se cambia el motor. Un motor nuevo no se
  compara con el anterior. La fecha de cambio sale de la planilla y la base de cambios de componentes.
- Parámetros de la etapa 1: los de VIMS ligados a señales del FMEA en `knowledge/fuentes/silver_798.yaml` (presión de
  aceite, temperaturas de refrigerante, admisión y escape, diferencial de escape, presión de admisión, restricción de
  filtro de aire), más los de contexto (filtros de aceite y combustible, temperatura ambiente).

## 4. Calidad antes de comparar

1. **Valores imposibles:** se descartan los centinelas (por ejemplo, -3277,4 en temperaturas de escape) y los picos
   fuera del rango físico de cada parámetro (rango POR_CALIBRAR con Monitoreo de Condiciones).
2. **Pocas lecturas:** un agregado diario con menos de N lecturas (`CountTrend`, N POR_CALIBRAR) no se compara.
3. **Sin datos:** un camión sin descargas en un día queda marcado; después de M días seguidos (POR_CALIBRAR) su
   estado es **sin datos**. Nunca se toma como normal.
4. **Regla de corte:** cada comparación usa solo datos anteriores a la fecha analizada (point-in-time).

## 5. Las cuatro comparaciones

Cada una responde una pregunta distinta y se calcula por separado. Ninguna necesita IA.

| # | Comparación | Cómo se calcula (PROPUESTA) | Necesita |
|---|---|---|---|
| 1 | **Contra un límite** | ¿El valor pasó un límite fijo? | Límites del fabricante o de Monitoreo de Condiciones. Hoy no existen para la mayoría de los parámetros VIMS: se usan donde los haya, y las alarmas VIMS (eventos) ya son límites del fabricante |
| 2 | **Contra su propia historia** | Desviación robusta respecto del mismo camión y condición: `(valor − mediana) / dispersión`, con la mediana y la dispersión (MAD) de una ventana previa de N días que deja fuera los últimos días | Solo la historia del camión. **No necesita límites ni unidades** |
| 3 | **Contra la flota** | La misma desviación robusta, pero contra los camiones del mismo modelo y contrato, ese día y en la misma condición | La flota. Tampoco necesita límites ni unidades |
| 4 | **Tendencia** | Pendiente robusta del parámetro en una ventana reciente (por ejemplo, 14 días; Theil-Sen), comparada con la variación normal del camión | La historia del camión |

- **Dirección:** cada desviación se registra con su sentido (sube o baja) y se cruza con la dirección de la señal en el
  FMEA (`components/motor_diesel/fmea.json`). Por ejemplo, para MFP-07 importa que la presión de aceite **baje**; que
  suba no es señal de ese modo.
- **Bandas de severidad** de las comparaciones 2 y 3 (POR_CALIBRAR): leve, moderada y alta, según el tamaño de la
  desviación robusta. Puntos de partida para calibrar: 2, 3 y 4 dispersiones.
- Las comparaciones 2 y 3 permiten **empezar sin límites definidos**. Es la respuesta a que hoy no existan herramientas
  ni límites para las desviaciones de VIMS.

## 5b. Análisis de aceite (SOS)

Monitoreo de Condiciones ya revisa cada muestra cuando llega; el monitor **no reemplaza esa revisión**. El aceite
entra como desviación por dos razones: para **cruzarlo con VIMS** (la regla (b) del semáforo: por ejemplo, Fe y Pb
subiendo mientras baja la presión de aceite es la firma de un modo FMEA) y para ver la **tendencia entre muestras**,
que al revisar una muestra a la vez no se ve.

- **Unidad:** cada muestra del motor (`ENG`), no cada día. Se usa desde su fecha de disponibilidad: fecha de muestra
  + 3 días (CONFIRMADO, contrato de datos). Entre muestras, el estado del aceite es el de la última muestra disponible.
- **Elementos:** los de las señales del FMEA (Fe, Cu, Pb, Si, Na, K, PQI, hollín, viscosidad), no los del feature
  importance del modelo anterior.
- **Comparación 1, límites:** los del laboratorio, precautorios y condenatorios. Para el aceite **sí hay límites**
  (CONFIRMADO: el modelo actual usa las veces sobre el condenatorio).
- **Comparación 2, su historia:** contra las muestras anteriores **del mismo motor**. Como los metales se acumulan
  mientras el aceite está en uso, se compara la **tasa por hora de aceite** (ppm por hora), no solo el nivel. Una
  muestra marcada como previa a un cambio de aceite (`Changed = Y`) cierra el período; la siguiente empieza de nuevo.
- **Comparación 3, la flota:** la tasa por hora de aceite contra motores del mismo modelo y contrato.
- **Comparación 4, tendencia:** aumento de la tasa en las últimas muestras del mismo motor.
- **Calidad:** se descartan horómetros que retroceden o en cero, y las muestras repetidas de la misma fecha se
  consolidan (calidad observada en `knowledge/fuentes/bronze_798.yaml`).
- **Comentario del laboratorio:** se guarda como evidencia para el especialista y para la IA; no se usa para calcular.
- **Evaluación de Monitoreo de Condiciones:** si su evaluación de cada muestra queda registrada en algún sistema
  (POR_CONFIRMAR), es un dato valioso: sirve para calibrar el monitor y para medir si coincide con el criterio experto.

## 6. Eventos VIMS

Los eventos ya son alarmas definidas por el fabricante. Por camión y evento se calcula: **veces** en la ventana,
**severidad** (`EventSeverity`, 1 a 3 en la muestra, CONFIRMADO) y **duración** acumulada (`EventDuration`; unidad
POR_CONFIRMAR). Un evento que antes no aparecía en ese camión, o que se vuelve más frecuente que en su historia, cuenta
como desviación.

## 7. Resumen por parámetro y fuente

Para cada camión, parámetro y ventana (7, 15 y 30 días; PROPUESTA):

- **Veces:** días con desviación.
- **Severidad:** la banda más alta alcanzada.
- **Permanencia:** días seguidos con desviación, hasta hoy.

Es el mismo patrón que usa el modelo productivo actual (`knowledge/fuentes/features_predictivo40.yaml`), pero calculado
en el proyecto, con reglas escritas y regla de corte.

## 8. Estado diario por camión (semáforo)

| Estado | Regla (PROPUESTA; umbrales POR_CALIBRAR) |
|---|---|
| ⚪ **Sin datos** | Sin descargas válidas en los últimos M días |
| 🟢 **Normal** | Sin desviaciones, o solo leves y aisladas |
| 🟡 **En observación** | Alguna desviación moderada o alta, o una leve que se repite, pero sin persistencia ni coincidencia |
| 🔴 **Alerta** | (a) desviación moderada o alta que persiste N días seguidos, o (b) dos o más señales del **mismo modo FMEA** desviadas en la dirección de ese modo en la misma ventana, o (c) un evento VIMS de severidad alta que se repite |

La regla (b) es la que conecta el monitor con el FMEA: varias señales de un mismo modo, cada una en su dirección,
suben la confianza de que hay algo real. Un camión pasa a rojo solo por **cambio de estado**, para que el especialista
reciba lo nuevo y no la misma alerta todos los días.

## 9. Qué entrega

**Tablas diarias** en el Lakehouse de Fabric (DP-005), versionadas y reproducibles:

1. `desviaciones`: camión, motor, fecha, parámetro, condición, valor, referencia propia, referencia de flota,
   desviación (propia, flota, tendencia), dirección, banda.
2. `estado_camion`: camión, fecha, estado, motivo (qué reglas se cumplieron), modos FMEA compatibles.

**Lista diaria de revisión para Monitoreo de Condiciones** (Power BI o un correo diario):

- Solo los camiones que cambiaron a alerta u observación, con lo nuevo arriba. El resto de la flota se resume en un
  conteo por estado.
- Por camión: qué parámetro, en qué condición de operación, desde qué fecha, cuánto se desvía de su historia y de la
  flota, y qué modo FMEA es compatible. Es la indicación de **dónde mirar** en las herramientas visuales que ya usan.
- Una vista de apoyo con el parámetro y sus bandas normales (propia y de flota), por si hace falta verlo ahí mismo.

**Presupuesto de alertas:** el número de camiones en la lista no puede superar lo que el equipo alcanza a revisar con
calidad. Ese número lo define Monitoreo de Condiciones (sección 12) y es un parámetro de diseño: los umbrales del
semáforo se calibran para respetarlo.

### 9b. De la alerta al caso

Cada camión en alerta abre un caso; si al día siguiente sigue en alerta, se actualiza el mismo caso (no se crea otro). Monitoreo de Condiciones lo confirma, descarta, deja en observación o pide información, e Ingeniería de Mantenimiento define la acción y el cierre. Los descartes con su motivo son el insumo principal para calibrar (sección 11). Estados, plazos y responsables en `docs/gestion/gobierno_piloto.md` (DP-008).

Un modo FMEA cuyas señales no se observan en los datos disponibles se informa como **no observable** para ese camión; el monitor no lo da por normal (DP-009).

## 10. Primer entregable: monitor VIMS y aceite para DMH

Etapa 1 completa (VIMS, flota DMH), antes del modelo predictivo y de la IA:

1. Leer las tendencias y eventos VIMS y el análisis de aceite de DMH con los filtros del contrato de datos, mediante
   la ingesta diaria con versiones y regla de corte (`docs/arquitectura/ingesta_monitor.md`, DP-010).
2. Calcular las comparaciones 2, 3 y 4 de VIMS (no necesitan límites), las cuatro del aceite (con los límites del
   laboratorio), los resúmenes de eventos y la regla de coincidencia entre VIMS y aceite.
3. Entregar las tablas y la lista diaria de revisión para Monitoreo de Condiciones.
4. Revisar con Monitoreo de Condiciones durante unas semanas qué desviaciones tienen sentido y ajustar los umbrales.

## 11. Calibración y validación

La prueba hacia atrás es el **reproceso histórico** del monitor: el mismo código re-ejecutado día por día con regla
de corte. Su resultado es también la entrada del entrenamiento del modelo (`docs/arquitectura/ciclo_aprendizaje.md`).

1. **Hacia atrás con las 10 fallas:** con datos solo anteriores a cada falla, ¿el monitor mostró desviaciones? ¿En qué
   parámetros, en qué dirección y con cuántos días de anticipación?
2. **Falsas alarmas:** en camiones y períodos sin falla, ¿cuántas alertas por camión al mes?
3. **Criterio experto:** Monitoreo de Condiciones revisa una muestra de desviaciones y dice cuáles son reales.

Con esos tres resultados se fijan los umbrales POR_CALIBRAR y se decide si el monitor pasa a uso diario.

## 12. Lo que necesitamos de Monitoreo de Condiciones

No se les pide más trabajo de revisión del que ya hacen: el monitor existe para reducirlo. Se les pide:

1. **Cuántos camiones por día o por semana pueden revisar con calidad** (el presupuesto de alertas).
2. Qué herramientas visuales usan hoy, para que la lista indique dónde mirar en ellas.
3. Rango físico y unidad de cada parámetro VIMS (para descartar valores imposibles).
4. Los límites que sí usan, donde existan (aceite, particulado, alarmas).
5. Revisar durante unas semanas las primeras listas y decir qué casos tenían sentido.
6. Si registran su evaluación de cada muestra de aceite, dónde queda, para usarla en la calibración.

## 13. Escala

- Mismo cálculo para 150–180 equipos: es aritmética por camión y día, sin IA, de bajo costo de cómputo.
- La flota de referencia (comparación 3) es por modelo y contrato: un 797F no se compara con un 798AC.
- El 797B tiene dos motores (ENG_FR y ENG_RR en SOS): cada uno es un componente propio con su historia.
