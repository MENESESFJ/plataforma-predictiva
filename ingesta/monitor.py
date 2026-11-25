"""Ingesta de las entradas del monitor de desviaciones: VIMS (tendencias y eventos) y aceite (SOS).

Mecanismo (DP-010, docs/arquitectura/ingesta_monitor.md):
1. Aterrizaje: copia íntegra e inmutable del archivo de origen, con su hash (solo lectura del origen, DP-001).
2. Estandarización: filtro de alcance (series de la flota, componente motor), formato largo común y
   marcas de calidad. Nada se borra: las filas dudosas quedan con valido = False y su motivo.
3. Vida de motor: cada fila se asigna al motor instalado a esa fecha (la historia se reinicia con el cambio).
4. Fusión con versiones: cada fila lleva fecha_evento, fecha_disponible y fecha_ingesta. Una corrección del
   origen agrega una versión nueva; nunca sobrescribe. Así una evaluación al corte ve lo que se sabía ese día.

Uso:
    python -m ingesta.monitor --fecha 2027-01-15 --tipo diario
    python -m ingesta.monitor --fecha 2027-01-04 --tipo historico
Rutas: INGESTA_ORIGEN (raíz del lake o del Lakehouse) e INGESTA_DESTINO (almacenamiento del proyecto).
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "components/motor_diesel/ingesta_monitor.yaml"

CLAVE = ["fuente", "serie_equipo", "fecha_evento", "parametro", "condicion", "id_registro"]
DATOS = ["valor", "n_lecturas", "severidad", "horas_aceite", "horas_maquina", "cambio_aceite", "comentario"]
COLUMNAS = (CLAVE[:2] + ["equipo", "vida_motor"] + CLAVE[2:] + DATOS
            + ["valido", "motivo", "hash_fila", "fecha_disponible", "fecha_ingesta", "lote_id"])
FUENTES_MONITOR = ["vims_tendencias", "vims_eventos", "sos"]


# --- configuración -------------------------------------------------------------------------------
def cargar_config(ruta: Path = CONFIG) -> dict:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def series_flota(cfg: dict) -> Dict[str, str]:
    """Serie del equipo -> código de equipo, desde la lista de la flota del piloto."""
    bronze = yaml.safe_load((RAIZ / cfg["flota"]).read_text(encoding="utf-8"))
    return {serie: equipo for equipo, serie in bronze["flota_dmh_798ac"]["equipos_piloto"].items()}


# --- lectura del origen --------------------------------------------------------------------------
def leer_origen(ruta: Path, formato: str) -> pd.DataFrame:
    """Lee el archivo tal como viene, todo como texto (la conversión es explícita después)."""
    if formato == "parquet":
        return pd.read_parquet(ruta).astype(str)
    if formato == "csv_punto_y_coma":
        return pd.read_csv(ruta, sep=";", dtype=str, keep_default_na=False)
    if formato == "csv_envuelto":  # cada fila entre comillas externas, con comillas internas dobladas
        lineas = []
        for linea in Path(ruta).read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if len(linea) >= 2 and linea[0] == linea[-1] == '"':
                linea = linea[1:-1].replace('""', '"')
            if linea:
                lineas.append(linea)
        return pd.read_csv(io.StringIO("\n".join(lineas)), dtype=str, keep_default_na=False)
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")


def _fecha(s: pd.Series, dayfirst: bool = False) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst).dt.normalize()


# --- estandarización -----------------------------------------------------------------------------
def _alcance(df: pd.DataFrame, c: dict, motor: str, series: Dict[str, str]) -> pd.DataFrame:
    """Solo la flota del piloto (por serie) y solo el motor."""
    serie = df[c["serie"]].str.strip().str.upper()
    return df[serie.isin(series) & (df[c["componente"]].str.strip() == motor)].assign(_serie=serie)


def _base(df: pd.DataFrame, fuente: str, c: dict, series: Dict[str, str]) -> pd.DataFrame:
    out = pd.DataFrame({"fuente": fuente, "serie_equipo": df["_serie"],
                        "equipo": df["_serie"].map(series), "fecha_evento": _fecha(df[c["fecha"]])})
    for col in COLUMNAS:
        if col not in out:
            out[col] = pd.NA
    out["condicion"] = df[c["condicion"]].str.strip() if "condicion" in c else ""
    out["id_registro"] = df[c["id_registro"]].str.strip() if "id_registro" in c else ""
    out["valido"], out["motivo"] = True, ""
    return out


def _invalidar(out: pd.DataFrame, mascara: pd.Series, motivo: str) -> None:
    m = mascara.fillna(False) & out["valido"]
    out.loc[m, "valido"] = False
    out.loc[m, "motivo"] = motivo


def estandarizar_vims(df: pd.DataFrame, fuente: str, cfg: dict, series: Dict[str, str]) -> pd.DataFrame:
    c = cfg["columnas"]
    df = _alcance(df, c, cfg["componente_motor"], series)
    out = _base(df, fuente, c, series)
    out["parametro"] = df[c["parametro"]].str.strip().values
    out["valor"] = _num(df[c["valor"]]).values
    if "n_lecturas" in c:
        out["n_lecturas"] = _num(df[c["n_lecturas"]]).values
    if "severidad" in c:
        out["severidad"] = _num(df[c["severidad"]]).values
    cal = cfg.get("calidad", {})
    _invalidar(out, out["fecha_evento"].isna(), "sin_fecha")
    _invalidar(out, out["valor"].isna(), "sin_valor")
    if "centinela_max" in cal:
        _invalidar(out, out["valor"] <= cal["centinela_max"], "centinela")
    if isinstance(cal.get("n_lecturas_min"), (int, float)):
        _invalidar(out, out["n_lecturas"] < cal["n_lecturas_min"], "pocas_lecturas")
    return out[COLUMNAS]


def estandarizar_sos(df: pd.DataFrame, cfg: dict, series: Dict[str, str]) -> pd.DataFrame:
    """Una fila por muestra y parámetro; el contexto de la muestra se repite en cada fila."""
    c = cfg["columnas"]
    df = _alcance(df, c, cfg["componente_motor"], series)
    partes = []
    for p in cfg["parametros"]:
        if p not in df:
            continue
        out = _base(df, "sos", c, series)
        out["parametro"] = p
        out["valor"] = _num(df[p]).values
        out["horas_aceite"] = _num(df[c["horas_aceite"]]).values
        out["horas_maquina"] = _num(df[c["horas_maquina"]]).values
        out["cambio_aceite"] = df[c["cambio_aceite"]].str.strip().str.upper().values
        out["comentario"] = df[c["comentario"]].values if c.get("comentario") in df else ""
        partes.append(out)
    if not partes:
        return pd.DataFrame(columns=COLUMNAS)
    out = pd.concat(partes, ignore_index=True)
    _invalidar(out, out["fecha_evento"].isna(), "sin_fecha")
    _invalidar(out, out["valor"].isna(), "sin_valor")
    # El horómetro en cero no invalida el nivel del elemento, pero sí el cálculo de tasas: se anota.
    sin_horas = (out["horas_maquina"] <= 0).fillna(False) & out["valido"]
    out.loc[sin_horas, "motivo"] = "horometro_cero"
    return out[COLUMNAS]


def cambios_de_motor(df: pd.DataFrame, cfg: dict, series: Dict[str, str]) -> pd.DataFrame:
    """Fechas de cambio de motor por serie de equipo, desde la base de cambios de componentes."""
    f = cfg["filtro"]
    m = (df["Contrato"].str.strip() == f["Contrato"]) & (df["Componentes"].str.strip().str.lower() == f["Componentes"])
    d = df[m]
    out = pd.DataFrame({"serie_equipo": d["SerialNumber"].str.strip().str.upper(),
                        "fecha_cambio": _fecha(d["FechaCambio"], dayfirst=True)})
    return out[out["serie_equipo"].isin(series) & out["fecha_cambio"].notna()]


def asignar_vida(tabla: pd.DataFrame, cambios: pd.DataFrame) -> pd.DataFrame:
    """vida_motor = <equipo>-v<n>, con n = cambios de motor hasta esa fecha (el día del cambio ya es el motor nuevo)."""
    tabla = tabla.copy()
    n = pd.Series(0, index=tabla.index)
    for serie, grupo in cambios.groupby("serie_equipo"):
        filas = tabla["serie_equipo"] == serie
        for fc in grupo["fecha_cambio"]:
            n[filas & (tabla["fecha_evento"] >= fc)] += 1
    tabla["vida_motor"] = tabla["equipo"].astype(str) + "-v" + n.astype(str)
    return tabla


# --- versiones y regla de corte ------------------------------------------------------------------
def _hash_filas(df: pd.DataFrame) -> pd.Series:
    texto = df[DATOS].astype(object).map(str).agg("|".join, axis=1)
    return texto.map(lambda t: hashlib.sha256(t.encode()).hexdigest()[:16])


def fusionar(historico: Optional[pd.DataFrame], nuevos: pd.DataFrame, fecha_lote: date, tipo: str,
             desfase_dias: int, ventana_dias: int, lote_id: str) -> Tuple[pd.DataFrame, dict]:
    """Agrega a la tabla las filas nuevas o corregidas, sin sobrescribir versiones anteriores.

    historico: fecha_disponible = fecha_evento + desfase (no hay registro de cuándo llegó cada fila).
    diario:    fecha_disponible = max(fecha_evento + desfase, fecha_lote); solo se releen los últimos
               ventana_dias. Un dato atrasado o corregido queda disponible desde el día en que llegó.
    """
    lote = pd.Timestamp(fecha_lote)
    nuevos = nuevos.copy()
    fuera = 0
    if tipo == "diario":
        dentro = nuevos["fecha_evento"] >= lote - pd.Timedelta(days=ventana_dias)
        fuera = int((~dentro).sum())
        nuevos = nuevos[dentro]
    nuevos["hash_fila"] = _hash_filas(nuevos) if len(nuevos) else pd.Series(dtype=str)
    disponible = nuevos["fecha_evento"] + pd.Timedelta(days=desfase_dias)
    nuevos["fecha_disponible"] = disponible if tipo == "historico" else disponible.where(disponible > lote, lote)
    nuevos["fecha_ingesta"], nuevos["lote_id"] = lote, lote_id
    nuevos = nuevos.drop_duplicates(CLAVE + ["hash_fila"])

    if historico is None or historico.empty:
        previo = pd.DataFrame(columns=CLAVE + ["hash_previo"])
        historico = pd.DataFrame(columns=COLUMNAS)
    else:
        previo = (historico.sort_values(["fecha_ingesta", "fecha_disponible"])
                  .drop_duplicates(CLAVE, keep="last")[CLAVE + ["hash_fila"]]
                  .rename(columns={"hash_fila": "hash_previo"}))
    m = nuevos.merge(previo, on=CLAVE, how="left")
    es_nueva, es_corregida = m["hash_previo"].isna(), m["hash_previo"].notna() & (m["hash_previo"] != m["hash_fila"])
    agregar = m[es_nueva | es_corregida][COLUMNAS]
    tabla = pd.concat([historico[COLUMNAS], agregar], ignore_index=True) if len(historico) else agregar.reset_index(drop=True)
    resumen = {"nuevas": int(es_nueva.sum()), "corregidas": int(es_corregida.sum()),
               "sin_cambio": int(len(m) - es_nueva.sum() - es_corregida.sum()), "fuera_de_ventana": fuera}
    return tabla, resumen


def vista_al_corte(tabla: pd.DataFrame, fecha_corte: date) -> pd.DataFrame:
    """Lo que se sabía al cierre de fecha_corte: la última versión disponible de cada fila."""
    t = tabla[tabla["fecha_disponible"] <= pd.Timestamp(fecha_corte)]
    return (t.sort_values(["fecha_disponible", "fecha_ingesta"])
            .drop_duplicates(CLAVE, keep="last").reset_index(drop=True))


def reporte_calidad(tabla: pd.DataFrame, fuente: str, series: Dict[str, str], fecha_lote: date,
                    dias_atraso_max: int = 2) -> dict:
    """Qué camiones tienen datos del día analizado (D-1) y si la fuente viene al día."""
    t = tabla[tabla["fuente"] == fuente]
    analizado = pd.Timestamp(fecha_lote) - pd.Timedelta(days=1)
    ultima = t["fecha_evento"].max()
    con_dato = set(t.loc[(t["fecha_evento"] == analizado) & t["valido"].astype(bool), "serie_equipo"])
    return {"fuente": fuente, "dia_analizado": analizado.date().isoformat(),
            "ultima_fecha": None if pd.isna(ultima) else ultima.date().isoformat(),
            "atrasada": bool(pd.isna(ultima) or ultima < analizado - pd.Timedelta(days=dias_atraso_max)),
            "equipos_sin_datos_dia_analizado": sorted(series[s] for s in series if s not in con_dato),
            "filas_invalidas_por_motivo": t.loc[~t["valido"].astype(bool), "motivo"].value_counts().to_dict()}


# --- ejecución -----------------------------------------------------------------------------------
def aterrizar(origen: Path, destino_dir: Path) -> dict:
    """Copia íntegra del archivo de origen (el origen solo se lee) y su huella."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / origen.name
    shutil.copy2(origen, destino)
    return {"archivo": str(destino), "sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
            "bytes": destino.stat().st_size}


def ejecutar(fecha_lote: date, tipo: str, origen: Path, destino: Path, cfg: Optional[dict] = None) -> dict:
    cfg = cfg or cargar_config()
    series = series_flota(cfg)
    lote_id = f"{fecha_lote:%Y%m%d}-{tipo}"
    reporte = {"lote_id": lote_id, "tipo": tipo, "fuentes": {}}

    fc = cfg["fuentes"]["cambios_motor"]
    copia = aterrizar(origen / fc["ruta"], destino / "entrada/aterrizaje/cambios_motor" / lote_id)
    cambios = cambios_de_motor(leer_origen(Path(copia["archivo"]), fc["formato"]), fc, series)

    for fuente in FUENTES_MONITOR:
        f = cfg["fuentes"][fuente]
        copia = aterrizar(origen / f["ruta"], destino / "entrada/aterrizaje" / fuente / lote_id)
        crudo = leer_origen(Path(copia["archivo"]), f["formato"])
        std = estandarizar_sos(crudo, f, series) if fuente == "sos" else estandarizar_vims(crudo, fuente, f, series)
        std = asignar_vida(std, cambios)
        ruta_tabla = destino / "entrada/estandar" / f"{fuente}.parquet"
        previo = pd.read_parquet(ruta_tabla) if ruta_tabla.exists() else None
        tabla, resumen = fusionar(previo, std, fecha_lote, tipo, f["desfase_disponible_dias"],
                                  f["ventana_relectura_dias"], lote_id)
        ruta_tabla.parent.mkdir(parents=True, exist_ok=True)
        tabla.to_parquet(ruta_tabla, index=False)
        reporte["fuentes"][fuente] = {"origen": copia, **resumen,
                                      "calidad": reporte_calidad(tabla, fuente, series, fecha_lote)}
    ruta_rep = destino / "entrada/reportes" / f"{lote_id}.json"
    ruta_rep.parent.mkdir(parents=True, exist_ok=True)
    ruta_rep.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    return reporte


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fecha", type=date.fromisoformat, default=date.today())
    ap.add_argument("--tipo", choices=["diario", "historico"], default="diario")
    ap.add_argument("--origen", default=os.environ.get("INGESTA_ORIGEN"))
    ap.add_argument("--destino", default=os.environ.get("INGESTA_DESTINO"))
    a = ap.parse_args(argv)
    if not a.origen or not a.destino:
        ap.error("faltan --origen/--destino (o INGESTA_ORIGEN/INGESTA_DESTINO)")
    rep = ejecutar(a.fecha, a.tipo, Path(a.origen), Path(a.destino))
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
