# Ciclo de aprendizaje del modelo

Dónde vive lo que el sistema aprende, cómo se incorporan las fallas históricas y nuevas, quién decide y cuándo se
ejecuta. Decisión: DP-011.

## 1. Qué aprende y dónde vive

| Qué | Dónde vive | Cómo cambia |
|---|---|---|
| **Monitor de desviaciones** (umbrales del semáforo, ventanas) | Configuración versionada en el repositorio | Calibración con Monitoreo de Condiciones (descartes, falsas alarmas); se aprueba y se versiona |
| **Modelo predictivo** (patrón de las desviaciones previas a una falla) | Registro de modelos de Azure ML (MLflow), versiones numeradas con alias `candidato` y `vigente` | Solo con el flujo de entrenamiento, el validador y la aprobación de Confiabilidad |
| **Agentes de IA** | No aprenden: no se reentrenan. Usan el FMEA y sus instrucciones, versionados en el repositorio | Cuando cambia el FMEA o las instrucciones |

La operación diaria **nunca modifica el modelo**. Usa la versión vigente hasta que una versión nueva la reemplace. La
anterior queda guardada y se puede volver a ella.

## 2. Cómo entran las fallas históricas: el reproceso del monitor

Antes de una falla no tenemos guardadas las desviaciones: hay que calcularlas. Por eso **se lee toda la historia
diaria de VIMS y aceite de cada vida de motor**, pero no se le entrega cruda al modelo. Pasa primero por el monitor,
día por día, como si estuviera operando en esa fecha:

```
Historia diaria (ingesta, DP-010)              Monitor, re-ejecutado día por día              Modelo
VIMS por día y condición, muestras de aceite ─► para cada día D, solo con lo disponible en D ─► aprende de
(toda la vida de cada motor)                    · desviación propia, de flota y tendencia       los resúmenes,
                                                · veces, severidad y permanencia (7/15/30 d)    no de la señal
                                                · semáforo y modos FMEA compatibles             cruda
```

- **Es el mismo código del monitor diario**, aplicado a fechas pasadas. No hay una lógica aparte para el
  entrenamiento: lo que el modelo aprende es exactamente lo que verá en operación.
- **Hay que leer todo** por tres razones:
  1. la comparación contra la propia historia necesita los días anteriores del mismo motor;
  2. la comparación contra la flota necesita a todos los camiones cada día;
  3. los motores que **no** fallaron enseñan cómo se ve un motor sano, lo que evita las falsas alarmas.
- **El volumen es manejable.** Se parte del agregado diario de Silver, no de las lecturas horarias. Para DMH son unos
  14 camiones × ~1.100 días × ~15 parámetros × ~4 condiciones: alrededor de 1 millón de filas diarias, minutos de
  cálculo. Para la flota de 150–180 camiones son unas 10 veces más; sigue siendo un proceso por lotes común.
- **El resultado del reproceso se guarda** como tabla de desviaciones históricas, identificada por la versión del
  monitor. Si los umbrales se recalibran, se re-ejecuta y queda una versión nueva; la anterior se conserva.
- **Es también la prueba hacia atrás** del monitor (tarea M3): el mismo reproceso muestra cuántos días antes de cada
  falla se habría encendido la alerta y cuántas falsas alarmas habría dado.

### Límites de la historia

- Los datos parten en 2023. Los motores instalados antes tienen su vida **observada solo en parte**: se usa desde el
  inicio de los datos y queda registrado.
- Un motor recién instalado no tiene historia propia. Sus primeros días (por ejemplo, 30; POR_CALIBRAR) quedan "sin
  referencia propia" y solo se comparan contra la flota.

## 3. Qué aprende el modelo: las etiquetas

Cada fila de entrenamiento es **una vida de motor en un día**, con los resúmenes del monitor de ese día. La etiqueta
responde a la pregunta del caso de uso:

| Situación de ese día | Etiqueta |
|---|---|
| El motor tuvo un cambio **imprevisto** dentro de los 15 días siguientes (horizonte por validar) | Positivo |
| Faltan más de 15 días para su cambio, o el motor sigue operando | Negativo |
| El motor salió por **PCR** (cambio programado) | Censura: sus días son negativos, pero el final de su vida no cuenta como falla |
| Días posteriores a la fecha del cambio | No existen para esa vida (empieza la vida siguiente) |

- La fecha y el tipo de cada cambio salen del listado de eventos validado (F01) y de la tabla de vidas de motor (D6).
- **AFA/RCA y la causa raíz solo etiquetan y validan; nunca son variables** (contrato de datos).
- El modo FMEA de cada falla sirve para revisar si el modelo se alerta por las señales correctas.

## 4. El flujo de entrenamiento

Es un proceso aparte del flujo diario (`TipoFlujo.ENTRENAMIENTO` en el supervisor) y **se invoca**: no corre solo.

| Paso | Qué hace | Resultado guardado |
|---|---|---|
| 1. Ingesta y calidad | Vista al corte de la historia (DP-010) | Versión de los datos |
| 2. Reproceso del monitor | Desviaciones históricas día por día | Tabla de desviaciones históricas, con la versión del monitor |
| 3. Variables y etiquetas | Resúmenes por vida y día, y etiqueta según el horizonte | Dataset de entrenamiento con su huella |
| 4. Modelamiento | Ajusta el modelo | Versión nueva en el registro con alias `candidato` |
| 5. Validador | Las pruebas de la sección 5 | Informe y veredicto técnico |
| 6. Aprobación | Confiabilidad revisa el informe | Si aprueba, el candidato pasa a `vigente` |

Cada versión del modelo registra con qué se hizo: versión de los datos, del monitor, del FMEA, del listado de eventos
y del código. Así cualquier resultado se puede reproducir y explicar.

## 5. El validador

Su pregunta es: **¿el modelo nuevo es mejor que lo que ya tenemos, sin trampas?** No incorpora la historia: decide
si el resultado de incorporarla es aceptable.

| Prueba | Criterio de aceptación (POR_ACORDAR con Confiabilidad en F04) |
|---|---|
| Sin fuga de información | Ninguna variable usa datos posteriores a la fecha evaluada; ninguna variable administrativa (AFA, causa raíz, OT de cambio) |
| Contra la referencia | Supera al baseline: la práctica actual (cambio por horas, 16.000 h ajustado por carga) y el semáforo del monitor por sí solo |
| Contra el vigente | No empeora al modelo vigente en anticipación ni en falsas alarmas |
| Anticipación | Días de alerta antes de cada una de las 10 fallas imprevistas |
| Falsas alarmas | Alertas por camión al mes en vidas y períodos sin falla, dentro del presupuesto de Monitoreo de Condiciones |
| Estabilidad | Con pocas fallas, se valida **dejando una falla fuera** cada vez (se entrena con 9 y se prueba con la décima) y se revisa por año |
| Señales correctas | Para cada falla con modo FMEA conocido, las señales que más pesan son coherentes con ese modo |

Veredicto: `aprobado_tecnicamente` o `rechazado`, con motivos. **La decisión de pasar a vigente es de Confiabilidad**,
nunca automática.

Hoy el validador del repositorio es un esqueleto (solo verifica que el modelo tenga variables y datos). Las pruebas de
esta tabla se construyen en la tarea P2.

## 6. Cuándo se invoca y quién

| Disparador | Quién lo invoca |
|---|---|
| Confiabilidad valida una falla nueva y la agrega al listado de eventos | Desarrollo, a pedido de Confiabilidad |
| Cambia el FMEA (por ejemplo, v1.1 con los modos nuevos) | Desarrollo |
| Se recalibra el monitor | Desarrollo |
| Revisión periódica: trimestral (PROPUESTA) | Desarrollo, con informe a Confiabilidad |
| El seguimiento detecta degradación (más falsas alarmas, fallas sin alerta) | Desarrollo o Monitoreo de Condiciones |

Cada falla nueva hace dos aportes: entra a la historia del próximo entrenamiento y se revisa en el caso abierto
(DP-008), donde se ve si el monitor la anticipó.

## 7. Expectativas con 10 fallas

Diez fallas imprevistas es poca historia para un modelo complejo. Por eso:

- El primer modelo es simple e interpretable: los resúmenes del monitor y unas pocas reglas o un modelo lineal o de
  supervivencia. No se usan redes neuronales.
- El valor inicial viene sobre todo del monitor (DP-006). El modelo mejora a medida que se acumulan fallas validadas.
- Al escalar a otros contratos 798AC, la historia de fallas crece y el modelo puede ganar precisión. Cada contrato
  conserva su propia validación (contrato de datos, tenant).
