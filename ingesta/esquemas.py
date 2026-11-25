"""Esquemas de las tablas que escribe la ingesta (DP-012).

Una tabla Delta exige tipos estables entre ejecuciones: cada tabla se conforma a su esquema antes de
escribirse. Este archivo es la referencia para revisar la estructura con el ingeniero de datos
(docs/arquitectura/fabric_estructura.md); una prueba verifica que la ingesta lo respete.
"""
from typing import Dict

import pandas as pd

# tipo lógico -> tipo pandas (y su equivalente Delta en el comentario)
TIPOS = {
    "texto": "string",            # STRING
    "decimal": "float64",         # DOUBLE
    "entero": "Int64",            # BIGINT
    "logico": "boolean",          # BOOLEAN
    "fecha": "date",              # DATE (día, sin hora ni zona: lo mejor soportado por el SQL endpoint y Power BI)
}

_ENTRADA = {
    "fuente": "texto", "serie_equipo": "texto", "equipo": "texto", "vida_motor": "texto",
    "fecha_evento": "fecha", "parametro": "texto", "condicion": "texto", "id_registro": "texto",
    "valor": "decimal", "n_lecturas": "decimal", "severidad": "decimal", "horas_aceite": "decimal",
    "horas_maquina": "decimal", "cambio_aceite": "texto", "comentario": "texto",
    "valido": "logico", "motivo": "texto", "hash_fila": "texto",
    "fecha_disponible": "fecha", "fecha_ingesta": "fecha", "lote_id": "texto",
}

ESQUEMAS: Dict[str, Dict[str, str]] = {
    # Plata: una tabla por fuente, mismo esquema (formato largo común)
    "entrada_vims_tendencias": _ENTRADA,
    "entrada_vims_eventos": _ENTRADA,
    "entrada_sos": _ENTRADA,
    # Cambios de motor no firmados por Confiabilidad (se reemplaza completa en cada lote)
    "eventos_pendientes_validacion": {
        "equipo": "texto", "serie_equipo": "texto", "fecha_cambio": "texto", "estado": "texto",
        "tipo_origen": "texto", "horas_motor_removido": "texto", "descripcion_origen": "texto",
        "lote_id": "texto",
    },
    # Bitácora de lotes: una fila por lote y fuente (seguimiento de la ingesta en Power BI)
    "ingesta_lotes": {
        "lote_id": "texto", "tipo": "texto", "fecha_lote": "fecha", "fuente": "texto",
        "archivo_origen": "texto", "sha256": "texto", "bytes": "entero",
        "nuevas": "entero", "corregidas": "entero", "sin_cambio": "entero", "fuera_de_ventana": "entero",
        "ultima_fecha": "texto", "atrasada": "logico", "n_equipos_sin_datos": "entero",
        "equipos_sin_datos": "texto", "filas_invalidas": "entero",
    },
}

TABLA_DE_FUENTE = {"vims_tendencias": "entrada_vims_tendencias", "vims_eventos": "entrada_vims_eventos",
                   "sos": "entrada_sos"}


def conformar(df: pd.DataFrame, tabla: str) -> pd.DataFrame:
    """Columnas en el orden del esquema y con su tipo; falla si falta una columna."""
    esquema = ESQUEMAS[tabla]
    faltan = [c for c in esquema if c not in df.columns]
    if faltan:
        raise ValueError(f"{tabla}: faltan columnas {faltan}")
    out = df[list(esquema)].copy()
    for col, tipo in esquema.items():
        if tipo == "fecha":
            out[col] = pd.to_datetime(out[col]).dt.date.astype(object)
        elif tipo == "texto":
            out[col] = out[col].astype("string").fillna("")
        elif tipo in ("decimal", "entero"):
            out[col] = pd.to_numeric(out[col], errors="coerce").astype(TIPOS[tipo])
        else:
            out[col] = out[col].astype(TIPOS[tipo])
    return out.reset_index(drop=True)


def a_pandas(df: pd.DataFrame, tabla: str) -> pd.DataFrame:
    """Al leer, las fechas vuelven a Timestamp para operar (comparaciones, ventanas)."""
    for col, tipo in ESQUEMAS[tabla].items():
        if tipo == "fecha" and col in df:
            df[col] = pd.to_datetime(df[col])
    return df
