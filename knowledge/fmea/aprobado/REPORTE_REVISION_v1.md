# FMEA motor – revisión aplicada (v1.0.0)

Revisión: `revision_fmea_confiabilidad_v1.xlsx`, aplicada el 2026-10-09.

## Resultado

- Modos predictivos aprobados: 8
- Síntomas aprobados: 102
- Síntomas eliminados: 5
- Síntomas pendientes: 6

Los modos se tomaron del bloque editado por Confiabilidad (encabezado `ID:`).

## Observaciones por modo

### MFP-01 desgaste_cojinetes (critica)
- Síntomas de soporte declarados que no están aprobados: SIN-013, SIN-016
- Modelos aplicables por criterio experto, sin síntoma documental: 794 AC, 798 AC
- Códigos SMCS no presentes en la matriz: 1000

### MFP-02 desgaste_camisas_anillos (alta)
- Síntomas de soporte declarados que no están aprobados: SIN-013, SIN-018
- Modelos aplicables por criterio experto, sin síntoma documental: 798 AC
- Códigos SMCS no presentes en la matriz: 1000, 1215

### MFP-03 contaminacion_refrigerante_en_aceite (alta)
- Síntomas de soporte declarados que no están aprobados: SIN-008, SIN-016
- Modelos aplicables por criterio experto, sin síntoma documental: 798 AC
- Códigos SMCS no presentes en la matriz: 1217
- Modos RCM padre pendientes de validar.

### MFP-04 ingreso_abrasivo_polvo (media)
- Síntomas de soporte declarados que no están aprobados: SIN-010, SIN-014, SIN-017, SIN-018, SIN-112
- Modelos aplicables por criterio experto, sin síntoma documental: 798 AC

### MFP-05 dilucion_combustible (alta)
- Modelos aplicables por criterio experto, sin síntoma documental: 794 AC, 798 AC

### MFP-06 sobrecalentamiento (alta)
- Modelos aplicables por criterio experto, sin síntoma documental: 798 AC

### MFP-07 baja_presion_lubricacion (critica)
- Modelos aplicables por criterio experto, sin síntoma documental: 794 AC, 798 AC

### MFP-08 combustion_deficiente (alta)
- Síntomas de soporte declarados que no están aprobados: SIN-074
- Modelos aplicables por criterio experto, sin síntoma documental: 793F Tier 4, 798 AC

## Síntomas pendientes

| ID | Síntoma | Corrección pedida | Comentario |
|---|---|---|---|
| SIN-013 | High levels of Metallic Particulate | REVISAR DIRECCIÓN | Mantener aumento sólo si particulado_inspeccion posee escala ordinal; de lo contrario usar presencia. |
| SIN-041 | FMI-05 - Electrical Problem | REVISAR DESCRIPCIÓN FMI-05 | La descripción Erratic Signal puede no representar correctamente FMI-05. Validar contra el código diagnóstico fuente. |
| SIN-074 | Exhaust Temperature equal to or less than 700°C | REVISAR DIRECCIÓN | El texto equal to or less than 700°C no sustenta inequívocamente temp_escape:aumento. |
| SIN-086 | Fuel High Temperature | REVISAR POSIBLE DUPLICADO | Comparar con SIN-095; ambos describen alta temperatura de combustible con planes similares. |
| SIN-095 | Fuel High Temperature | REVISAR POSIBLE DUPLICADO | Comparar con SIN-086; conservar sólo si aporta origen o plan de acción diferente. |
| SIN-112 | Patch test with presence of Silica (Si) | REVISAR VARIABLE Y UNIDAD | Patch test con presencia de sílice puede requerir variable silica_particulado:presencia y unidad evento, no si_ppm. |

## Síntomas eliminados

| ID | Síntoma | Motivo |
|---|---|---|
| SIN-008 | Sodium (Na) High Values | Inconsistencia entre modo de origen y síntoma; cubierto por SIN-003 y SIN-009. |
| SIN-012 | High levels of wear | Registro genérico sin variable, dirección ni unidad. |
| SIN-014 | Contamination by Dust | Contradicción entre contaminación por agua y contaminación por polvo. |
| SIN-016 | Sodim (Na) and Cupper (Cu) High Values | Mezcla Na y Cu y mecanismos diferentes; cubierto por síntomas específicos. |
| SIN-018 | Iron (Fe) High Values | Duplica hierro elevado sin aportar mayor especificidad. |

## Modos RCM

La hoja 'Modos RCM' no fue revisada: la regla de severidad H/S/E/O sigue sin validar. Las severidades de los modos predictivos son las asignadas por Confiabilidad.
