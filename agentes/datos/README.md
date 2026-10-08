# Agente 2: Ingesta de Datos

## Propósito
Extraer, unificar y generar un snapshot inmutable de datos históricos y operacionales para un componente y fecha de corte específicos, garantizando el principio *Point-in-Time*.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (SQL, Spark, Conectores).
- **Uso de LLM:** Ninguno.

## Responsabilidades
1. Cargar las consultas versionadas desde el SET del componente (`data_sources.sql`).
2. Conectarse a fuentes oficiales (Snowflake, Databricks, Historiadores, SAP PM / Maximo).
3. Aplicar filtro estricto de fecha de corte (`point-in-time`): prohibido incluir registros posteriores a `fecha_corte`.
4. Exportar snapshot persistido y calcular su hash SHA-256 (`hash_snapshot`).

## Interacción con el SET del Componente
- Consume: `components/<componente_id>/data_sources.sql` y `definition.json`.

## Salida
- `dataset_id`, `hash_snapshot`, recuento de registros, metadatos de fuentes integradas.
