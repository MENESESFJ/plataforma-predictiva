# Conocimiento FMEA – Motor CAEX

Flujo de la información de modos de falla, desde los documentos de Confiabilidad hasta el FMEA que consume el modelo.

```text
fuentes/ → convertir_fmea.py → borrador/ → Confiabilidad → revision/ → aplicar_revision.py → aprobado/ + components/motor_diesel/fmea.json
(original)                     (propuesto)                 (planilla)                        (registro)   (runtime)
```

## `fuentes/` – documentos originales (no editar)

| Archivo | Contenido | Uso |
|---|---|---|
| `FMEA_Memoria_798AC.xlsx` | Memoria RCM 798AC: hoja de información, hoja de decisión, estrategia y FMECA consolidada por sistema | Estructura de modos, consecuencias H/S/E/O, tareas e intervalos, código SMCS por subunidad |
| `FMECA_Lists_ENG.xlsx` | Lista por componente y condición (793F/794AC/797F/798AC): rutina, modo, síntoma, plan de acción | Síntomas observables (variable y dirección), fuente de datos (SOS, VIMS, particulado) y planes de acción |

Si llega una nueva versión de un documento, se reemplaza el archivo y se vuelve a ejecutar el conversor; el historial queda en git.

## `borrador/` – generado, estado `propuesto`

Se regenera con:

```bash
python herramientas/fmea/convertir_fmea.py
```

- `fmea_borrador.json`: modos predictivos propuestos, modos RCM y síntomas, con trazabilidad a hoja y fila de origen.
- `revision_fmea_confiabilidad.xlsx`: planilla para que Confiabilidad apruebe o corrija (columnas amarillas).

Nada de `borrador/` se usa en runtime.

## `revision/` – planillas devueltas por Confiabilidad

Se guardan tal como llegan, versionadas (`revision_fmea_confiabilidad_v1.xlsx`, `_v2`, …). Son el registro de la aprobación.

## `aprobado/` – FMEA aprobado

Se genera con:

```bash
python herramientas/fmea/aplicar_revision.py --revision knowledge/fmea/revision/revision_fmea_confiabilidad_v1.xlsx
```

- `fmea_motor_v1.json`: registro completo, con modos aprobados, síntomas aprobados, pendientes y eliminados, y observaciones.
- `REPORTE_REVISION_v1.md`: resumen legible de lo aplicado y de lo pendiente.
- Además, el script actualiza `components/motor_diesel/fmea.json`, la versión reducida que lee el agente de Interpretación.

Reglas: solo entran los modos con `Aprobado = S`. Los síntomas en `N` se eliminan y los que tengan otro valor quedan pendientes. El soporte de cada modo se recalcula solo con síntomas aprobados. Si la revisión afirma algo sin respaldo documental (modelos aplicables, códigos SMCS que no están en la matriz), se conserva, pero queda como observación.

## Pendientes tras la revisión v1

Ver `aprobado/REPORTE_REVISION_v1.md`. En resumen:

- Seis síntomas en revisión: dirección de `particulado_inspeccion`, temperatura de escape ≤ 700 °C, posible duplicado de temperatura de combustible, sílice en patch test y descripción de FMI-05.
- El 798AC figura como modelo aplicable en los 8 modos por criterio experto, aunque las fuentes no documentan síntomas de ese modelo.
- Los códigos SMCS 1000, 1215 y 1217 no están en la matriz SMCS, y el código 1050 está descrito de forma distinta en la memoria RCM y en la matriz.
- La hoja de Modos RCM no se revisó, así que la regla de severidad H/S/E/O sigue sin validar.
- Los ID cambiaron de MF-00x a MFP-0x. La homologación SMCS se migró y conserva el ID anterior en `id_fmea_anterior`.
