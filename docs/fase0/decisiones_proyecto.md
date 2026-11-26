# Decisiones del proyecto y procesos a rearmar

Registro de decisiones de alcance y método que no son del FMEA (las del FMEA están en
`knowledge/fmea/revision/decisiones.json`). Cada decisión indica quién la tomó y cuándo.

Principio: el proyecto no toca nada de lo existente y documenta todo lo que tenga que reconstruir.

## Decisiones

| ID | Decisión | Motivo | Estado |
|---|---|---|---|
| DP-001 | **No se modifica ningún proceso, tabla ni modelo existente.** Bronze, Silver, Gold y los modelos productivos se leen, nunca se escriben ni se reconfiguran. | Los procesos existentes son corporativos y están en producción; un cambio no controlado afecta a otros usuarios. | ✅ Responsable del proyecto, 2026-10-14 |
| DP-002 | **Lo que haya que rearmar se construye dentro de este proyecto,** con código versionado, pruebas y regla de corte, y se registra en la tabla de abajo. | Que cada proceso quede documentado, reproducible y auditable. | ✅ Responsable del proyecto, 2026-10-14 |
| DP-003 | **Las anomalías se generan de cero en este proyecto** (candidato). Las de Gold se usan solo como comparación. | No se conoce cómo se calcularon, qué límites usan ni si respetan la fecha de corte. | 🟡 Propuesta; confirmar al revisar Gold |
| DP-004 | **No se describe el contenido de un archivo sin haberlo revisado.** Lo no revisado queda como POR_REVISAR. | Evitar supuestos que después se tomen como hechos. | ✅ Responsable del proyecto, 2026-10-14 |
| DP-005 | **El proyecto no depende de una plataforma de cómputo.** Rutas de datos, dirección de MLflow y conexiones se configuran; el código lee Delta, Parquet o CSV por ruta. Destino: Fabric para datos y resultados, Azure ML para modelos. | Databricks y Synapse se decomisan; la plataforma cambia durante el proyecto. | ✅ Responsable del proyecto, 2026-11-24 |
| DP-006 | **El monitor de desviaciones es un entregable propio para Monitoreo de Condiciones,** además de insumo del modelo predictivo: revisa a diario todos los camiones y entrega la lista corta de los que hay que mirar, en qué parámetro y desde cuándo. Es el primer entregable (VIMS y aceite de DMH; el aceite entra para cruzarlo con VIMS y ver su tendencia, sin reemplazar la revisión de cada muestra). | Monitoreo de Condiciones tiene herramientas visuales para revisar un camión, pero no capacidad para revisar a diario 150–180 equipos. Las comparaciones contra la propia historia y la flota no requieren límites previos. | ✅ Responsable del proyecto, 2026-11-25 |
| DP-007 | **Un baseline de desarrollo nunca se presenta como modelo aprobado.** Si no hay modelo vigente, la inferencia usa el baseline, lo marca (`es_baseline`) y deja una advertencia visible en el estado de la ejecución. | Que nadie tome una referencia de desarrollo por una predicción validada. | ✅ Responsable del proyecto, 2026-11-25 (implementado) |
| DP-008 | **En el piloto los casos se gestionan en una tabla simple con estados** (pendiente, en observación, requiere información, confirmada, descartada, escalada, cerrada). Una alerta repetida actualiza el caso abierto; no crea otro. La integración con avisos y órdenes de trabajo de SAP queda para la operación. | Demostrar el ciclo alerta → revisión → acción → hallazgo sin esperar integraciones. Detalle en `docs/gestion/gobierno_piloto.md`. | 🟡 Propuesta; ratificar en el kickoff |
| DP-009 | **Un modo FMEA sin variable observable se declara no observable** por la plataforma; no se infiere por aproximación. | Evitar explicaciones sin respaldo en datos. | 🟡 Propuesta; aplicar en FMEA v1.1 (F03) |
| DP-010 | **Mecanismo de ingesta del monitor:** cada día se copia el archivo de origen (con su huella), se estandariza a un formato largo común con marcas de calidad y vida de motor, y se fusiona con versiones. Cada fila lleva fecha de evento, de disponibilidad y de ingesta; una corrección agrega una versión, nunca sobrescribe. Entradas de la etapa 1: `ds_Trends_798` y `ds_EventDuration_798` (Silver) y `datasetSOS798.csv` (Bronze). | Los orígenes no traen fecha de carga y pueden cambiar o apagarse; sin copia propia ni versiones, la prueba hacia atrás no es reproducible ni respeta la regla de corte. Detalle en `docs/arquitectura/ingesta_monitor.md`. | 🟡 Propuesta; implementado con datos sintéticos, falta validar con datos reales (M1) |
| DP-011 | **Ciclo de aprendizaje:** el modelo aprende solo en el flujo de entrenamiento, que se invoca (falla nueva validada, cambio de FMEA, recalibración del monitor o revisión trimestral). La historia entra re-ejecutando el monitor día por día con regla de corte; el modelo aprende de los resúmenes de desviaciones, no de la señal cruda. El validador emite un veredicto técnico y Confiabilidad aprueba el paso a vigente; la operación diaria nunca modifica el modelo. | Lo aprendido debe ser reproducible, comparable con la versión anterior y reversible. Detalle en `docs/arquitectura/ciclo_aprendizaje.md`. | 🟡 Propuesta; criterios del validador se acuerdan en F04 y se construyen en P2 |
| DP-012 | **Estructura en Fabric:** un workspace por ambiente (`ws-pp-dev`, `ws-pp-prod`); Lakehouse de entrada `lh_pp_entrada` (bronce en Files/, plata en tablas Delta) y Lakehouse del monitor `lh_pp_monitor` (oro, para Power BI); acceso al lake actual por shortcut de OneLake en solo lectura; notebooks de Python que llaman al paquete del proyecto, orquestados por un pipeline diario. Esquemas de tablas versionados en `ingesta/esquemas.py`. | Validar con Ingeniería de Datos la adopción de Fabric antes de construir el monitor; el mismo código corre hoy en local (Parquet) y en Fabric (Delta). Detalle y preguntas abiertas en `docs/arquitectura/fabric_estructura.md`. | 🟡 Propuesta; revisar con Ingeniería de Datos |

## Procesos a rearmar

| Proceso | Qué hace hoy (según lo conocido) | Por qué se rearma | Insumo | Estado |
|---|---|---|---|---|
| Ingesta de entradas del monitor | Silver agrega VIMS a diario; no registra cuándo llegó cada dato | Regla de corte y reproducibilidad (DP-010) | `ds_Trends_798`, `ds_EventDuration_798`, `datasetSOS798.csv`, base de cambios | 🟡 Diseñado e implementado (`ingesta/monitor.py`); falta validar con datos reales |
| Detección de anomalías en tendencias | Evalúa cada tendencia en el período y registra cuando escapa de su límite | Límites, ventanas y fecha de registro desconocidos (DP-003) | `ds_Trends_798` (Silver) | 🟡 Diseñado: `docs/arquitectura/monitor_desviaciones.md`; por construir |
| Agregados de eventos | Veces, severidad y permanencia de alarmas | Igual que tendencias | `ds_EventDuration_798` (Silver) | ⬜ Por diseñar |
| Agregados de rellenos | Litros acumulados, veces, severidad (> 90 L) | Igual que tendencias | `datasetOilrefill798` (Bronze) | ⬜ Por diseñar |
| Agregados SOS | Nivel actual, acumulado y veces sobre límite condenatorio | Elementos elegidos por el FMEA, no por el feature importance anterior; límites por confirmar | SOS Bronze / Silver | ⬜ Por diseñar |
| Gestión de casos | Hoy no existe un registro estructurado de alertas, decisiones y hallazgos | Cerrar el ciclo y aprender de los descartes (DP-008) | Lista diaria del monitor; decisiones de Monitoreo de Condiciones e Ingeniería | 🟡 Diseñado: `docs/gestion/gobierno_piloto.md`; por construir |
| Agregados de particulado | Severidad y veces | Origen actual en Cat Inspect (SQL Server); unir con el histórico de Argos | Cat Inspect `dbo.Inspection` + `dbo.InspectionQuestion` (preguntas de motor); Argos | ⬜ Falta dominio de respuestas |

Cada proceso rearmado debe quedar con: definición escrita, código en el repositorio, pruebas,
regla de corte explícita y comparación contra el resultado de Gold cuando exista.

## Por revisar (sin especular)

- `gold/amt/798/ds_SumMaintenance_798.csv`: revisar contenido real (2026-10-15).
- Demás `ds_Sum*_798` de Gold: revisar estructura antes de decidir DP-003.
