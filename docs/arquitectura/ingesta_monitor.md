# Ingesta de las entradas del monitor de desviaciones

Cómo llegan cada día los datos de VIMS y del aceite al monitor de desviaciones (`monitor_desviaciones.md`), sin
modificar nada de lo existente (DP-001) y sin depender de una plataforma (DP-005). Decisión: DP-010.

- **Configuración:** `components/motor_diesel/ingesta_monitor.yaml`
- **Código:** `ingesta/monitor.py` (Python portable; pruebas en `tests/test_ingesta_monitor.py`)

Marcas: CONFIRMADO · PROPUESTA · POR_CALIBRAR · POR_CONFIRMAR.

## 1. Qué entra

| Fuente | Dataset de origen | Granularidad | Por qué este dataset |
|---|---|---|---|
| Tendencias VIMS | `ds_Trends_798` (Silver, Foresight) | Camión · día · parámetro · condición de operación | Ya viene en la unidad de análisis del monitor. Es un promedio diario, no una anomalía: DP-003 no lo afecta |
| Eventos VIMS | `ds_EventDuration_798` (Silver, Foresight) | Camión · día · evento | Alarmas del fabricante con severidad y duración |
| Aceite (SOS) | `datasetSOS798.csv` (Bronze, Foresight) | Una fila por muestra con todos los elementos | Trae en una fila los elementos, las horas de aceite, el cambio de aceite y el comentario del laboratorio. En Silver hay un archivo por elemento |
| Cambios de motor | `BaseCambiosComponentes798.csv` (Bronze, contratos) | Un cambio por fila | Reinicia la historia de cada camión cuando se cambia el motor. Se reemplaza por la tabla de vidas de motor (tarea D6) cuando esté validada |

Foresight tiene prioridad sobre Argos (CONFIRMADO). El particulado (Cat Inspect y Argos) y los rellenos entran en la
etapa 2 con el mismo mecanismo.

**Riesgo:** no conocemos cómo Silver calcula el promedio diario de `ds_Trends_798`. Antes del piloto se compara con
las tendencias de Bronze en una muestra de camiones y días (POR_CONFIRMAR). Si no coincide, se agrega desde Bronze
con el mismo mecanismo.

## 2. El mecanismo, en cuatro pasos

```
 Lake actual / Fabric          Almacenamiento del proyecto (Lakehouse)
 (solo lectura)
 ┌───────────────┐  1. copia  ┌────────────────────┐  2-3. estandariza   ┌──────────────────────┐  4. corte   ┌─────────┐
 │ ds_Trends_798 │ ─────────► │ aterrizaje/<lote>/ │ ──────────────────► │ estandar/<fuente>    │ ──────────► │ Monitor │
 │ ds_EventDur.. │   + hash   │ (copia inmutable)  │  alcance, calidad,  │ (con versiones y     │  lo que se  └─────────┘
 │ datasetSOS798 │            └────────────────────┘  vida de motor      │  3 fechas por fila)  │  sabía al día
 └───────────────┘                                                       └──────────────────────┘
                                                      reporte de calidad del lote ──► reportes/<lote>.json
```

1. **Aterrizaje.** Se copia el archivo de origen completo a una carpeta del lote, con su huella SHA-256. El origen
   solo se lee. Así cada resultado del monitor se puede reproducir con los mismos datos, aunque el origen cambie o se
   apague (Databricks se retira en 2027).
2. **Estandarización.**
   - Se filtra el alcance por la serie del equipo (lista de la flota) y por el componente motor (`1000.00.CC.0 MOTOR`
     en Silver, `ENG` en SOS). El código de equipo se toma de la serie, porque en el origen varía (`MH340` o
     `MH-340`).
   - Todas las fuentes quedan en un formato largo común: camión, motor instalado, fecha, parámetro, condición, valor y
     contexto (horas de aceite, cambio de aceite, severidad del evento).
   - Se marcan los problemas de calidad sin borrar nada. Una fila dudosa queda con `valido = False` y su motivo:
     centinela (por ejemplo -3277,4), pocas lecturas en el día, sin valor, sin fecha. En SOS también se anota el
     horómetro en cero.
3. **Vida de motor.** Cada fila se asigna al motor instalado en esa fecha (`MH340-v0`, `MH340-v1`…). El día del cambio
   ya pertenece al motor nuevo. Un motor nuevo no se compara con el anterior.
4. **Versiones y regla de corte.** Cada fila lleva tres fechas:

| Fecha | Qué es |
|---|---|
| `fecha_evento` | Cuándo ocurrió (día del agregado VIMS, fecha de la muestra de aceite) |
| `fecha_disponible` | Desde cuándo se puede usar en una evaluación |
| `fecha_ingesta` | Qué día la trajo la ingesta (lote) |

Si el origen corrige un valor, se agrega una **versión nueva**; la anterior no se borra. El monitor lee siempre la
"vista al corte": la última versión disponible al cierre del día evaluado. Una prueba hacia atrás ve exactamente lo
que se sabía ese día.

## 3. Cómo se calcula la fecha de disponibilidad

| Tipo de carga | Regla | Por qué |
|---|---|---|
| **Histórica** (una vez, con la copia del histórico, tarea D1) | `fecha_evento + desfase` | No hay registro de cuándo llegó cada fila en el pasado |
| **Diaria** | `máx(fecha_evento + desfase, día de la ingesta)` | Un dato que llega atrasado o corregido queda disponible desde el día en que llegó, no desde su fecha de evento |

| Fuente | Desfase | Estado |
|---|---|---|
| VIMS (tendencias y eventos) | 1 día | POR_CALIBRAR: medir con las primeras semanas de cargas diarias |
| Aceite (SOS) | 3 días desde la muestra | CONFIRMADO (contrato de datos) |

## 4. Ejecución diaria

| Elemento | Definición |
|---|---|
| Frecuencia | Diaria (PROPUESTA) |
| Hora | 07:00, después de la actualización de Silver y Bronze (POR_CONFIRMAR la hora real de actualización) |
| Día evaluado | El día anterior (D-1), con lo disponible al correr |
| Relectura | Cada día se releen los últimos 15 días de VIMS y 60 de aceite, para capturar descargas atrasadas y correcciones. Lo que cambie más atrás se cuenta en el reporte y no se carga |
| Idempotencia | Correr dos veces el mismo lote no duplica filas |
| Falla | 1 reintento a las 2 horas; si vuelve a fallar, la fuente queda **atrasada** y se informa |

**Reporte de calidad de cada lote** (`reportes/<lote>.json`), por fuente:
- filas nuevas, corregidas, sin cambio y fuera de la ventana de relectura;
- última fecha recibida, y si la fuente está atrasada;
- camiones sin datos en el día evaluado;
- filas inválidas por motivo.

El monitor usa este reporte para el estado **sin datos**. Un camión o una fuente sin datos se informa; nunca se toma
como normal.

## 4b. Aviso de cambio de motor

En cada ejecución, la ingesta compara la base de cambios de componentes con el listado de eventos de motor
(`docs/fase0/eventos_motor_dmh_798_borrador.csv`, donde Confiabilidad firma en `validado_por` y
`fecha_validacion`). Todo cambio que no esté validado queda en `entrada/eventos/pendientes_validacion.csv`:

| Estado | Qué significa | Qué hace Confiabilidad |
|---|---|---|
| `nuevo` | Está en la base de cambios y no en el listado | Lo agrega al listado, lo clasifica y lo firma |
| `sin_validar` | Está en el listado, sin firma | Lo revisa y lo firma |

- Un cambio y una fila del listado son el mismo evento si coinciden la serie del equipo y la fecha, con una tolerancia
  de 3 días (PROPUESTA), porque las fechas pueden diferir entre fuentes.
- Cada pendiente trae el contexto del origen para quien valida: tipo de detención, horas del motor y descripción.
- El reporte del lote cuenta los nuevos y los sin validar, y detalla los nuevos.
- Solo los eventos firmados entran al entrenamiento como etiqueta (`eventos_validados`, DP-011). Un pendiente igual
  separa las vidas de motor en el monitor: el cambio físico ocurrió aunque falte clasificarlo.

## 5. Dónde corre

| Etapa | Origen (`INGESTA_ORIGEN`) | Destino (`INGESTA_DESTINO`) | Quién lo programa |
|---|---|---|---|
| Hoy, hasta tener el workspace (D2) | Lake actual (solo lectura) | Almacenamiento del proyecto | Ejecución manual o programada que solo llama a `python -m ingesta.monitor` |
| Con Fabric (D2) | OneLake (acceso directo al lake o tablas migradas) | Lakehouse del proyecto, tablas Delta | Pipeline programado de Fabric que ejecuta el mismo módulo |
| Cat Inspect (etapa 2) | SQL Server, por copia programada de Fabric | Igual | Pipeline de Fabric |

El código es el mismo en todas las etapas; solo cambian las rutas. No se usa nada exclusivo de Databricks (DP-005).

Comandos:

```
python -m ingesta.monitor --tipo historico --fecha <día de la copia del histórico>   # una vez (D1)
python -m ingesta.monitor --tipo diario                                               # cada día
```

## 6. Pendientes para cerrar el mecanismo

| Pendiente | Responsable | Tarea |
|---|---|---|
| Rutas físicas y acceso de lectura a los tres datasets | TI / Datos | D1 |
| Hora de actualización diaria de Silver y Bronze | TI / Datos | D1 |
| Comparar el promedio diario de Silver con Bronze en una muestra | Desarrollo | M1 |
| Rangos físicos por parámetro (además del centinela) | Monitoreo de Condiciones | D5 |
| Tabla de vidas de motor validada | Confiabilidad + Componentes | D6 |
| Desfase real de VIMS, medido con las primeras cargas diarias | Desarrollo | M1 |
| Confirmar St = hollín y V100 = viscosidad en SOS | Monitoreo de Condiciones | D7 |
