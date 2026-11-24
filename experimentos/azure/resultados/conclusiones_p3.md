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

## Próximos pasos

1. Repetir los casos 0, 3 y 4 con las instrucciones ajustadas y comparar.
2. Probar `--esfuerzo low` contra `medium` en el caso 4 para medir si se pierde precisión.
3. Correr la prueba 2 (los 14 casos, 3 repeticiones), si está permitido enviar el texto técnico.
