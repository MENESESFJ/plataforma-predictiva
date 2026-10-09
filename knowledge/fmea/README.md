# Conocimiento FMEA – Motor CAEX

Flujo de la información de modos de falla, desde los documentos de Confiabilidad hasta el FMEA que consume el modelo.

```text
fuentes/   →  herramientas/fmea/convertir_fmea.py  →  borrador/  →  revisión Confiabilidad  →  components/motor_diesel/fmea.json
(original)                                            (propuesto)                              (aprobado, runtime)
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

Nada de `borrador/` se usa en runtime. Solo lo aprobado se traslada a `components/motor_diesel/fmea.json`.

## Hallazgos pendientes de revisión

- La lista de síntomas no documenta síntomas de aceite ni de particulado para el 798AC; la evidencia de los modos predictivos proviene de 793F/794AC/797F.
- 14 modos RCM tienen un código SMCS que no está en la matriz SMCS (entre ellos 1000, motor completo).
- El código 1050 figura como "admisión y escape" en la memoria RCM y como "entrega y dosificación de combustible" en la matriz SMCS.
- La severidad sugerida sale de una regla H/S/E/O que debe validar Confiabilidad.
