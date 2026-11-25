# Costo de la IA por análisis (estimación y medición)

## Precio de referencia (noviembre de 2026)

Azure, despliegue Global Standard, USD por millón de tokens. Confirmar en la calculadora de precios de Azure antes
de presupuestar: cambia seguido.

| Modelo | Entrada | Salida |
|---|---|---|
| gpt-5 (el usado en las pruebas) | 1,25 | 10,00 |
| gpt-5-mini | 0,25 | 2,00 |
| gpt-5-nano | 0,05 | 0,40 |

**Los tokens de razonamiento de gpt-5 se cobran como salida.** En nuestras pruebas son la mayor parte del costo.

## Estimación por análisis

Medida sobre los prompts y las respuestas reales de la séptima corrida (aproximación de 3,8 caracteres por token).
Los tokens de razonamiento no aparecen en el texto: el rango es una estimación para el esfuerzo medio.

| | Prueba 3: análisis de un caso (3 agentes) | Prueba 2: clasificar un cambio (1 llamada) |
|---|---|---|
| Tokens de entrada | 1.000 – 1.800 | ~1.000 (el FMEA va en las instrucciones) |
| Tokens de salida visibles | ~600 – 650 | ~200 |
| Tokens de razonamiento (medio) | ~3.000 – 7.500 (estimado) | ~500 – 2.000 (estimado) |
| **Costo con gpt-5** | **~US$ 0,04 – 0,09** | **~US$ 0,01 – 0,025** |
| Costo con gpt-5-mini | ~US$ 0,01 – 0,02 | ~US$ 0,002 – 0,005 |

- Si un agente copia al anterior (eco), el flujo se repite hasta 3 veces: el caso peor de la prueba 3 es ~US$ 0,27.
- La prueba 2 completa (14 cambios × 3 repeticiones = 42 llamadas) cuesta ~US$ 0,40 – 1,00.

## Proyección de uso

La IA solo trabaja sobre casos con alerta; el cálculo numérico de anomalías no usa IA.

| Escenario | Análisis por año | Costo anual aproximado (gpt-5) |
|---|---|---|
| 5 casos con alerta por semana | ~260 | US$ 10 – 25 |
| 1 análisis diario por camión (14 camiones) | ~5.100 | US$ 200 – 470 |
| Flota completa de varios contratos, 1 diario por camión (100 camiones) | ~36.500 | US$ 1.500 – 3.300 |

No incluye la plataforma de datos (Fabric, almacenamiento) ni Azure ML, que se cobran aparte.

## Palancas de costo

1. **Esfuerzo de razonamiento** (`--esfuerzo`): es la mayor palanca. Bajarlo de medio a bajo reduce mucho los tokens de
   salida; medir antes si se pierde precisión (comparar con los resultados guardados).
2. **Modelo**: gpt-5-mini cuesta un quinto. Probarlo con `--modelo` sobre los mismos casos.
3. **Solo casos con alerta**: no analizar toda la flota cada día.
4. **Evitar repeticiones por eco**: la salida estructurada por agente las reduce.

## Medición real

Desde esta versión, cada corrida registra los tokens que informa Azure y el costo estimado:

- Prueba 3: línea "Consumo: …" al inicio de cada resultado. Incluye las corridas repetidas por eco.
- Prueba 2: línea "Consumo: …" en `p2_resumen_<modelo>.md`, con el total de las llamadas.

Los precios usados se pueden cambiar sin tocar el código, en el `.env`:

```
PRECIO_ENTRADA_USD_1M=1.25
PRECIO_SALIDA_USD_1M=10.0
```

Con dos o tres corridas medidas se reemplaza la estimación de esta página por el promedio real.
