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

## Procesos a rearmar

| Proceso | Qué hace hoy (según lo conocido) | Por qué se rearma | Insumo | Estado |
|---|---|---|---|---|
| Detección de anomalías en tendencias | Evalúa cada tendencia en el período y registra cuando escapa de su límite | Límites, ventanas y fecha de registro desconocidos (DP-003) | `ds_Trends_798` (Silver) | ⬜ Por diseñar |
| Agregados de eventos | Veces, severidad y permanencia de alarmas | Igual que tendencias | `ds_EventDuration_798` (Silver) | ⬜ Por diseñar |
| Agregados de rellenos | Litros acumulados, veces, severidad (> 90 L) | Igual que tendencias | `datasetOilrefill798` (Bronze) | ⬜ Por diseñar |
| Agregados SOS | Nivel actual, acumulado y veces sobre límite condenatorio | Elementos elegidos por el FMEA, no por el feature importance anterior; límites por confirmar | SOS Bronze / Silver | ⬜ Por diseñar |
| Agregados de particulado | Severidad y veces | Origen actual en Cat Inspect (SQL Server) | Cat Inspect | ⬜ Pendiente de acceso |

Cada proceso rearmado debe quedar con: definición escrita, código en el repositorio, pruebas,
regla de corte explícita y comparación contra el resultado de Gold cuando exista.

## Por revisar (sin especular)

- `gold/amt/798/ds_SumMaintenance_798.csv`: revisar contenido real (2026-10-15).
- Demás `ds_Sum*_798` de Gold: revisar estructura antes de decidir DP-003.
