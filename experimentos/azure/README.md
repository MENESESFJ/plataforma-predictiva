# Experimentos en Azure AI Foundry (VM de capacitación)

Pruebas cortas para validar, con herramientas de Azure, piezas que el proyecto usará desde 2027.
Corren en la VM de capacitación (acceso temporal de 6 meses); **los resultados se suben al repo**
para que no se pierdan cuando cierre el acceso.

## Reglas

- **Datos:** la VM es de un tenant de capacitación. Solo se usa lo que ya está en el repositorio y
  datos sintéticos. No se suben exportes del lake, SOS ni planillas.
- La prueba 2 envía solo texto técnico de los 14 cambios de motor (sin equipo, serie ni fechas).
  Confirmar antes que está permitido enviarlo a un modelo del tenant de capacitación.
- **Sin claves en el código ni en el repo:** todo por variables de entorno.
- No se modifica nada de la plataforma corporativa (DP-001).

## Preparación (una vez)

```bash
git clone https://github.com/MENESESFJ/plataforma-predictiva.git
cd plataforma-predictiva
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux: source .venv/bin/activate)
pip install -r requirements.txt -r experimentos/azure/requirements-azure.txt
python -m pytest -q               # deben pasar todos los tests
```

Variables (en Windows: `set NOMBRE=valor`; en Linux: `export NOMBRE=valor`):

| Variable | De dónde sale | Prueba |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Portal de Foundry → el despliegue de GPT-5 → Endpoint (`https://<recurso>.openai.azure.com/`) | 2 |
| `AZURE_OPENAI_DEPLOYMENT` | Nombre del despliegue (por defecto `gpt-5`) | 2 |
| `AZURE_OPENAI_API_KEY` | Clave del despliegue. Si no se define, usa la sesión de `az login` | 2 |
| `AZURE_OPENAI_API_VERSION` | Opcional; por defecto `2025-04-01-preview` | 2 |
| `MLFLOW_TRACKING_URI` | Azure ML studio → workspace → "MLflow tracking URI" (`azureml://...`) | 1 |

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

```bash
python -m experimentos.azure.p2_clasificar_causas --repeticiones 3
```

Pide al modelo, a ciegas, el grupo de falla y los modos FMEA de cada uno de los 14 cambios de motor, y
lo compara con la propuesta manual (`docs/fase0/eventos_motor_dmh_798_borrador.csv`).

- Mide **acierto** (coincidencia con la propuesta manual) y **consistencia** (misma respuesta en las 3 repeticiones).
- Las diferencias no son automáticamente errores del modelo: se revisan con Confiabilidad.
- Resultados: `resultados/p2_clasificacion_<modelo>.csv` y `resultados/p2_resumen_<modelo>.md`.
- Para comparar modelos (hay ~45 disponibles), repetir con `--modelo <otro_despliegue>`.

## Al terminar

```bash
git checkout -b experimentos/resultados-azure
git add experimentos/azure/resultados
git commit -m "Resultados de experimentos en Azure"
git push -u origin experimentos/resultados-azure
```

O copiar los archivos de `resultados/` y compartirlos para subirlos.

## Pruebas siguientes (después de 1 y 2)

3. Demo del patrón de traspaso (Microsoft Agent Framework): triage + 2 especialistas, con casos sintéticos.
4. Índice de Azure AI Search con el FMEA y las causas raíz, para un agente de evidencia.

Ver `docs/arquitectura/patrones_orquestacion.md`.
