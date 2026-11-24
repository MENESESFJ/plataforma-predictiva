# Experimentos en Azure AI Foundry (VM de capacitación)

Pruebas cortas para validar, con herramientas de Azure, piezas que el proyecto usará desde 2027.
Corren en la VM de capacitación (acceso temporal de 6 meses); **los resultados se suben al repo**
para que no se pierdan cuando cierre el acceso.

## Reglas

- **Datos:** la VM es de un tenant de capacitación. Solo se usa lo que ya está en el repositorio y
  datos sintéticos. No se suben exportes del lake, SOS ni planillas.
- Las pruebas 2 y 3 envían solo texto técnico de los 14 cambios de motor (sin equipo, serie ni fechas).
  Confirmar antes que está permitido enviarlo a un modelo del tenant de capacitación.
- **Sin claves en el código ni en el repo:** todo por variables de entorno.
- No se modifica nada de la plataforma corporativa (DP-001).

## Preparación (una vez)

Mismo entorno del laboratorio 08 de Microsoft Learn (Agent Framework, multi-agentes): **Python 3.13**,
proyecto de Foundry con el modelo `gpt-5` desplegado y `az login`.

```powershell
git clone https://github.com/MENESESFJ/plataforma-predictiva.git
cd plataforma-predictiva
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r experimentos/azure/requirements-azure.txt
python -m pytest -q               # deben pasar todos los tests
az login
```

Crear un archivo `.env` en la raíz del repo (está en `.gitignore`, no se sube), con los mismos valores
del laboratorio:

```
AZURE_AI_PROJECT_ENDPOINT=<endpoint del proyecto: Foundry Toolkit → Copy Project Endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-5
MLFLOW_TRACKING_URI=<solo prueba 1: Azure ML studio → workspace → MLflow tracking URI>
```

No se usan claves: la autenticación es la sesión de `az login`, como en el laboratorio.

## Prueba 1: registro de modelos en Azure ML

```bash
python -m experimentos.azure.p1_registro_azureml
```

Corre el flujo del Supervisor con datos sintéticos: entrenamiento → candidato → vigente → inferencia.
Responde: ¿el registro de MLflow de Azure ML acepta los alias `candidato` y `vigente` sin cambiar código?

- Requiere un **workspace de Azure ML** (o un proyecto de Foundry basado en hub, que trae uno).
  Si la VM solo tiene un proyecto de Foundry sin workspace, la prueba queda **bloqueada**: anotarlo.
- Resultado: `experimentos/azure/resultados/p1_registro_azureml.json`.

## Prueba 2: clasificación de causas con GPT-5

```powershell
python -m experimentos.azure.p2_clasificar_causas --repeticiones 3
```

Un agente de Agent Framework clasifica, a ciegas, el grupo de falla y los modos FMEA de cada uno de los
14 cambios de motor, con salida estructurada, y se compara con la propuesta manual
(`docs/fase0/eventos_motor_dmh_798_borrador.csv`).

- Mide **acierto** (coincidencia con la propuesta manual) y **consistencia** (misma respuesta en las 3 repeticiones).
- Las diferencias no son automáticamente errores del modelo: se revisan con Confiabilidad.
- Resultados: `resultados/p2_clasificacion_<modelo>.csv` y `resultados/p2_resumen_<modelo>.md`.
- Para comparar modelos (hay ~45 en el catálogo), desplegar otro y repetir con `--modelo <despliegue>`.

## Prueba 3: análisis secuencial de un caso (patrón del laboratorio)

```powershell
python -m experimentos.azure.p3_analisis_secuencial --caso 4
```

El mismo `SequentialBuilder` del laboratorio, con tres agentes del dominio:
**evidencia** (hechos del registro, sin interpretar) → **fmea** (modos compatibles o modo nuevo) →
**revisor** (rol de Confiabilidad: qué está sustentado y qué verificar con SOS, Cat Inspect, eventos).

- `--caso` es la fila del listado de eventos (0 a 13). Sugeridos: 4 (MH344 2024, cojinetes),
  3 (MH345, bloqueo hidráulico), 0 (MH341 2023, distribución).
- Resultado: `resultados/p3_caso_<n>_<modelo>.md`. Es una demo del patrón, no un diagnóstico.

## Despliegue usado

`gpt-5`, versión 2025-08-07, Global Standard, 200.000 tokens y 2.000 solicitudes por minuto. Por defecto los
scripts usan razonamiento medio (`--esfuerzo medium`) y hasta 8.000 tokens de respuesta (`--max-tokens`).
**Esa versión de gpt-5 se retira el 2027-02-08** y el despliegue se actualiza solo a la siguiente: anotar la
versión del modelo al comparar resultados de fechas distintas.

## Problemas frecuentes

| Mensaje | Causa | Qué hacer |
|---|---|---|
| `429 rate_limit_exceeded` | Se superó el límite de tokens por minuto del despliegue (bajo en suscripciones de capacitación) | Casi siempre es el TPM del despliegue (por defecto 1.000, insuficiente): subir **Tokens per Minute** en Foundry (el proyecto usa 200.000). Los scripts reintentan solos (hasta 4 veces). Con cuota baja: `--esfuerzo low --max-tokens 3000`, `--pausa 20` en la prueba 2, o `gpt-5-mini` con `--modelo gpt-5-mini` |
| `... was disallowed by policy` al crear recursos | La suscripción del curso solo permite los recursos entregados | Usar el grupo de recursos y el proyecto del curso |
| `KeyError: 'AZURE_AI_PROJECT_ENDPOINT'` | No se encontró el `.env` | Crearlo en la raíz del repo y correr desde esa carpeta |

## Al terminar

```bash
git checkout -b experimentos/resultados-azure
git add experimentos/azure/resultados
git commit -m "Resultados de experimentos en Azure"
git push -u origin experimentos/resultados-azure
```

O copiar los archivos de `resultados/` y compartirlos para subirlos.

## Pruebas siguientes

4. Patrón de traspaso (`HandoffBuilder`, disponible en la misma versión): triage + especialistas por grupo de falla.
5. Índice de Azure AI Search con el FMEA y las causas raíz, para un agente de evidencia.

Ver `docs/arquitectura/patrones_orquestacion.md`.
