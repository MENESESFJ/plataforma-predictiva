# Estructura en Microsoft Fabric (propuesta para revisar con Ingeniería de Datos)

Propuesta de cómo se ubica el proyecto en Fabric: workspaces, Lakehouses, accesos al lake actual, tablas, notebooks,
pipeline y permisos. Decisión: DP-012. Todo nombre y valor de este documento es **PROPUESTA** hasta revisarlo con el
ingeniero de datos (sección 10).

- **Código que ya escribe en esta estructura:** `ingesta/monitor.py`, `ingesta/almacen.py` y `ingesta/esquemas.py`
  (Parquet en local, Delta en Fabric; probado con `deltalake`).
- **Plantilla de notebook:** `fabric/notebooks/nb_ingesta_monitor.py`.
- **Configuración:** `components/motor_diesel/ingesta_monitor.yaml`.

## 1. Vista general

```
Lake actual (ADLS, hoy usado por Databricks)          Workspace ws-pp-<ambiente>
  bronze/  silver/   (solo lectura)                   ┌───────────────────────────────────────────────────────────┐
        │                                             │ lh_pp_entrada                       lh_pp_monitor          │
        └── acceso directo (shortcut) ──────────────► │  Files/origen  (shortcut, lectura)   Tables/desviaciones    │
                                                      │  Files/aterrizaje (bronce, copia)    Tables/estado_camion   │
Cat Inspect (SQL Server), etapa 2                     │  Files/reportes, Files/eventos       Tables/casos (DP-008)  │
        └── copia programada (Data Factory) ────────► │  Tables/entrada_* (plata)                 │                 │
                                                      │  Tables/eventos_pendientes_validacion     │                 │
                                                      │  Tables/ingesta_lotes                     ▼                 │
                                                      │                         Modelo semántico (Direct Lake)      │
                                                      │ pl_monitor_diario: nb_ingesta_monitor → nb_monitor → aviso  │
                                                      └───────────────────────────────────────────────────────────┘
                                                                         │                         │
                                                              Azure ML (modelos, DP-011)     Power BI: lista diaria
```

## 2. Workspaces y ambientes

| Workspace | Para qué | Cuándo |
|---|---|---|
| `ws-pp-dev` | Desarrollo y pruebas con copia de datos | Desde D2 |
| `ws-pp-prod` | Operación del piloto: pipeline diario y Power BI para Monitoreo de Condiciones | Desde el piloto (M5) |

Un ambiente de pruebas separado (TEST) se agrega antes de pasar a operación (`gobierno_piloto.md`, sección 8). La
capacidad de Fabric (SKU) la define TI.

## 3. Lakehouses

| Lakehouse | Capa | Contenido | Quién lo lee |
|---|---|---|---|
| `lh_pp_entrada` | Bronce y plata | Copia de los archivos de origen, tablas estandarizadas, aviso de cambios de motor y bitácora de lotes | Monitor, entrenamiento, Desarrollo |
| `lh_pp_monitor` | Oro | Resultados: desviaciones, estado por camión, casos | Power BI, Monitoreo de Condiciones, agentes |

Se separan para dar permisos distintos: Power BI y los usuarios de negocio solo leen `lh_pp_monitor`.

**Alternativa a evaluar:** un solo Lakehouse con esquemas (`entrada`, `monitor`), si la función de esquemas está
habilitada en el tenant.

## 4. Acceso al lake actual (origen)

- **Acceso directo (shortcut) de OneLake** en `lh_pp_entrada/Files/origen`, apuntando a la cuenta de almacenamiento
  del lake actual, con `bronze/` y `silver/` debajo. No copia datos y es de solo lectura (DP-001).
- Si el shortcut no es posible (red, permisos, tipo de cuenta), la alternativa es una copia programada de Data Factory
  a `Files/origen`. El código no cambia: solo lee la ruta.
- Cuando el pipeline corporativo Predictivo 4.0 migre a Fabric, el shortcut se reapunta a las tablas migradas.

## 5. Tablas del Lakehouse de entrada (plata)

Formato Delta. Los esquemas viven en `ingesta/esquemas.py`; la ingesta conforma los tipos antes de escribir. Fechas
como `DATE` (día, sin hora ni zona), el tipo mejor soportado por el endpoint SQL y Power BI.

| Tabla | Escritura | Clave | Contenido |
|---|---|---|---|
| `entrada_vims_tendencias` | Solo agrega filas | fuente, serie_equipo, fecha_evento, parametro, condicion, id_registro | Promedio diario por parámetro y condición de operación |
| `entrada_vims_eventos` | Solo agrega filas | Igual | Eventos VIMS: severidad y duración |
| `entrada_sos` | Solo agrega filas | Igual (id_registro = Id Lab.) | Una fila por muestra y elemento, con horas de aceite y cambio de aceite |
| `eventos_pendientes_validacion` | Se reemplaza en cada lote | serie_equipo, fecha_cambio | Cambios de motor sin firma de Confiabilidad |
| `ingesta_lotes` | Reemplaza las filas del lote | lote_id, fuente | Bitácora: archivo, huella, filas nuevas y corregidas, atraso, camiones sin datos |

Columnas de las tres tablas `entrada_*` (formato largo común):

| Columna | Tipo | Columna | Tipo |
|---|---|---|---|
| fuente | STRING | horas_aceite | DOUBLE |
| serie_equipo | STRING | horas_maquina | DOUBLE |
| equipo | STRING | cambio_aceite | STRING |
| vida_motor | STRING | comentario | STRING |
| fecha_evento | DATE | valido | BOOLEAN |
| parametro | STRING | motivo | STRING |
| condicion | STRING | hash_fila | STRING |
| id_registro | STRING | fecha_disponible | DATE |
| valor | DOUBLE | fecha_ingesta | DATE |
| n_lecturas | DOUBLE | lote_id | STRING |
| severidad | DOUBLE | | |

**Versiones:** una corrección del origen agrega una fila con otra `fecha_ingesta`; nada se actualiza ni se borra. La
"vista al corte" (última versión con `fecha_disponible` ≤ fecha evaluada) se calcula al leer. El historial propio de
Delta (time travel) es un respaldo; el proyecto no depende de él, porque `VACUUM` lo limpia.

**Particionado:** ninguno para DMH (~1 millón de filas). Al escalar a 150–180 camiones, evaluar particionar por año
de `fecha_evento`.

## 6. Tablas del Lakehouse del monitor (oro)

Se definen al construir el monitor (M2). Propuesta según `monitor_desviaciones.md`, sección 9:

| Tabla | Contenido |
|---|---|
| `desviaciones` | Camión, motor, fecha, parámetro, condición, valor, referencias propia y de flota, desviaciones, dirección y banda |
| `estado_camion` | Camión, fecha, semáforo, motivo y modos FMEA compatibles |
| `casos` | Ciclo de casos del piloto (DP-008): estado, responsable, decisiones y cierre |

## 7. Ejecución: notebooks y pipeline

| Elemento | Tipo en Fabric | Qué hace |
|---|---|---|
| `nb_ingesta_monitor` | Notebook de Python, Lakehouse por defecto `lh_pp_entrada` | Llama a `ingesta.monitor.ejecutar(..., formato="delta")` y devuelve un resumen |
| `nb_monitor` | Notebook (M2) | Calcula desviaciones y semáforo; escribe en `lh_pp_monitor` |
| `pl_monitor_diario` | Pipeline de Data Factory | Programado a diario, 07:00 hora de Chile (POR_CONFIRMAR): `nb_ingesta_monitor` → `nb_monitor` → aviso por Teams o correo si hay fuentes atrasadas, cambios de motor nuevos o una falla |
| `pl_carga_historica` | Pipeline, ejecución manual única | `nb_ingesta_monitor` con `tipo = "historico"` (D1) |

- **Notebook de Python y no de Spark:** el volumen de DMH es chico y el código es pandas. Si al escalar hace falta, el
  mismo código corre en un notebook de Spark sin cambios de lógica.
- **El código del proyecto llega a Fabric como paquete:**
  1. GitHub Actions construye el wheel de `plataforma-predictiva`;
  2. se carga en un **Entorno de Fabric** (`env_pp`) junto con `deltalake`;
  3. los notebooks usan ese entorno.

  Así el notebook no contiene lógica y el código queda versionado y probado en el repositorio.
- **Integración con Git:** los notebooks y pipelines del workspace se pueden versionar con la integración Git de Fabric
  (GitHub o Azure DevOps), en la carpeta `fabric/` del repositorio.

## 8. Seguridad y permisos

| Rol | Acceso |
|---|---|
| Desarrollo | Colaborador en `ws-pp-dev`; lectura en `ws-pp-prod` |
| Ingeniería de Datos / TI | Administrador de ambos workspaces |
| Identidad del pipeline | Identidad del workspace o principal de servicio con lectura sobre el lake actual (para el shortcut) |
| Monitoreo de Condiciones, Confiabilidad | Lector del modelo semántico y del informe; sin acceso a `lh_pp_entrada` |

- Credenciales en Azure Key Vault o en conexiones de Fabric; nunca en el código ni en los notebooks.
- El origen solo se lee (DP-001).

## 9. Migración desde hoy

| Paso | Dónde corre | Destino |
|---|---|---|
| Hoy, hasta tener el workspace | Python sobre el lake actual (`INGESTA_FORMATO=parquet`) | Carpeta del proyecto con la misma estructura `Files/` y `Tables/` |
| D2: workspace habilitado | `nb_ingesta_monitor` en `ws-pp-dev` | `lh_pp_entrada` (Delta) |
| D1: carga histórica | `pl_carga_historica` | `lh_pp_entrada` |
| M5: piloto | `pl_monitor_diario` en `ws-pp-prod` | `lh_pp_entrada` y `lh_pp_monitor` |

## 10. Preguntas para el ingeniero de datos

1. ¿Se puede crear un shortcut de OneLake a la cuenta de almacenamiento del lake actual (`bronze/`, `silver/`)? ¿Con
   qué identidad y qué permisos?
2. ¿Qué pasa con el lake actual cuando se retire Databricks: se mantiene la cuenta de almacenamiento o se migra a
   OneLake? ¿Quién migra el pipeline Predictivo 4.0 y en qué fecha?
3. ¿A qué hora queda actualizado cada día Silver (`ds_Trends_798`, `ds_EventDuration_798`) y Bronze
   (`datasetSOS798.csv`)? ¿Se reescriben completos o se agregan filas?
4. ¿Cómo calcula Silver el promedio diario de las tendencias (`AverageTrend`, `CountTrend`) desde Bronze?
5. ¿Hay convención corporativa de nombres para workspaces, Lakehouses, notebooks y pipelines?
6. ¿Un Lakehouse por capa o uno con esquemas? ¿Está habilitada la función de esquemas de Lakehouse en el tenant?
7. ¿Qué capacidad de Fabric (SKU) se asigna al proyecto y se comparte con otros?
8. ¿Cómo se instalan paquetes propios en un Entorno de Fabric en la organización (wheel, feed privado)?
9. ¿Se usa la integración Git de Fabric? ¿Con GitHub Enterprise o Azure DevOps?
10. ¿Cómo se conecta Fabric a SQL Server de Cat Inspect (gateway de datos, red privada)?
11. ¿Qué política de retención y `VACUUM` se aplica a las tablas Delta?
12. ¿Cómo se envían avisos desde un pipeline (Teams, correo) en la organización?
