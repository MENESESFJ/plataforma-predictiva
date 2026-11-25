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
Rutas: INGESTA_ORIGEN (raíz del lake de origen o del acceso directo en OneLake) e INGESTA_DESTINO (raíz del
Lakehouse de entrada: Files/ y Tables/). INGESTA_FORMATO: parquet (local) o delta (Fabric). Ver DP-012.
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

from ingesta.almacen import Almacen
from ingesta.esquemas import TABLA_DE_FUENTE

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
    # Contexto para quien valida (si el origen lo trae): tipo, horas y descripción de la falla.
    for destino, origen in [("tipo_origen", "TipoDetencion"), ("horas_motor_removido", "HorasCompRemovido"),
                            ("descripcion_origen", "DescripcionFalla")]:
        out[destino] = d[origen].str.strip() if origen in d else ""
    out = out[out["serie_equipo"].isin(series) & out["fecha_cambio"].notna()]
    out["equipo"] = out["serie_equipo"].map(series)
    return out.reset_index(drop=True)


# --- aviso de cambio de motor (DP-011, paso 1: detectar) -----------------------------------------
def leer_listado_eventos(ruta: Path) -> pd.DataFrame:
    """Listado de eventos de motor (Confiabilidad firma en validado_por y fecha_validacion)."""
    ls = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    ls["serie_equipo"] = ls["serie_equipo"].str.strip().str.upper()
    ls["fecha_retiro"] = _fecha(ls["fecha_retiro"])
    ls["validado"] = ls["validado_por"].str.strip() != ""
    return ls


def eventos_pendientes(cambios: pd.DataFrame, listado: pd.DataFrame, tolerancia_dias: int) -> pd.DataFrame:
    """Cambios de motor que aún no pueden entrar al entrenamiento.

    - nuevo: está en la base de cambios y no en el listado de eventos (hay que agregarlo y validarlo).
    - sin_validar: está en el listado, pero Confiabilidad no lo ha firmado.
    Un cambio y una fila del listado son el mismo evento si coinciden la serie y la fecha (± tolerancia).
    """
    filas = []
    for _, c in cambios.iterrows():
        mismos = listado[(listado["serie_equipo"] == c["serie_equipo"])
                         & ((listado["fecha_retiro"] - c["fecha_cambio"]).abs() <= pd.Timedelta(days=tolerancia_dias))]
        if len(mismos) and mismos["validado"].any():
            continue
        filas.append({"equipo": c["equipo"], "serie_equipo": c["serie_equipo"],
                      "fecha_cambio": c["fecha_cambio"].date().isoformat(),
                      "estado": "sin_validar" if len(mismos) else "nuevo",
                      "tipo_origen": c["tipo_origen"], "horas_motor_removido": c["horas_motor_removido"],
                      "descripcion_origen": c["descripcion_origen"]})
    cols = ["equipo", "serie_equipo", "fecha_cambio", "estado", "tipo_origen", "horas_motor_removido",
            "descripcion_origen"]
    return pd.DataFrame(filas, columns=cols).sort_values(["estado", "fecha_cambio"], ignore_index=True)


def eventos_validados(listado: pd.DataFrame) -> pd.DataFrame:
    """Los únicos eventos que el entrenamiento puede usar como etiqueta (DP-011)."""
    return listado[listado["validado"]].reset_index(drop=True)


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


def _normalizar_clave(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos estables en la clave, venga la tabla de Parquet, de Delta o recién estandarizada."""
    df = df.copy()
    for col in CLAVE:
        if col.startswith("fecha"):
            df[col] = pd.to_datetime(df[col]).astype("datetime64[us]")
        else:
            df[col] = df[col].astype("string").fillna("").astype(object)
    for col in ("fecha_disponible", "fecha_ingesta"):
        if col in df:
            df[col] = pd.to_datetime(df[col]).astype("datetime64[us]")
    return df


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

    nuevos = _normalizar_clave(nuevos)
    if historico is not None and not historico.empty:
        historico = _normalizar_clave(historico)
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


def _fila_lote(lote_id: str, tipo: str, fecha_lote: date, fuente: str, info: dict) -> dict:
    cal = info.get("calidad", {})
    sin_datos = cal.get("equipos_sin_datos_dia_analizado", [])
    return {"lote_id": lote_id, "tipo": tipo, "fecha_lote": pd.Timestamp(fecha_lote), "fuente": fuente,
            "archivo_origen": info["origen"]["archivo"], "sha256": info["origen"]["sha256"],
            "bytes": info["origen"]["bytes"], "nuevas": info.get("nuevas", 0),
            "corregidas": info.get("corregidas", 0), "sin_cambio": info.get("sin_cambio", 0),
            "fuera_de_ventana": info.get("fuera_de_ventana", 0), "ultima_fecha": cal.get("ultima_fecha") or "",
            "atrasada": bool(cal.get("atrasada", False)), "n_equipos_sin_datos": len(sin_datos),
            "equipos_sin_datos": ";".join(sin_datos),
            "filas_invalidas": int(sum(cal.get("filas_invalidas_por_motivo", {}).values()))}


def ejecutar(fecha_lote: date, tipo: str, origen: Path, destino: Path, cfg: Optional[dict] = None,
             formato: Optional[str] = None) -> dict:
    """Un lote de ingesta. destino es la raíz del Lakehouse de entrada (Files/ y Tables/)."""
    cfg = cfg or cargar_config()
    almacen = Almacen(destino, formato)
    series = series_flota(cfg)
    lote_id = f"{fecha_lote:%Y%m%d}-{tipo}"
    reporte = {"lote_id": lote_id, "tipo": tipo, "formato": almacen.formato, "fuentes": {}}
    filas_lote = []

    # Bronce: copia del origen. Cambios de motor: vidas y aviso de pendientes.
    fc = cfg["fuentes"]["cambios_motor"]
    copia = aterrizar(origen / fc["ruta"], almacen.carpeta("aterrizaje", "cambios_motor", lote_id))
    cambios = cambios_de_motor(leer_origen(Path(copia["archivo"]), fc["formato"]), fc, series)
    filas_lote.append(_fila_lote(lote_id, tipo, fecha_lote, "cambios_motor", {"origen": copia}))
    aviso = cfg["aviso_cambio_motor"]
    pendientes = eventos_pendientes(cambios, leer_listado_eventos(RAIZ / aviso["listado_eventos"]),
                                    aviso["tolerancia_dias"]).assign(lote_id=lote_id)
    almacen.escribir("eventos_pendientes_validacion", pendientes, modo="overwrite")
    ruta_pend = almacen.archivos("eventos", "pendientes_validacion.csv")
    pendientes.to_csv(ruta_pend, index=False, encoding="utf-8-sig")  # copia para abrir en Excel
    reporte["eventos_pendientes"] = {"nuevos": int((pendientes["estado"] == "nuevo").sum()),
                                     "sin_validar": int((pendientes["estado"] == "sin_validar").sum()),
                                     "archivo": str(ruta_pend),
                                     "nuevos_detalle": pendientes[pendientes["estado"] == "nuevo"].to_dict("records")}

    # Plata: una tabla por fuente, solo se agregan filas (nuevas o versiones corregidas).
    for fuente in FUENTES_MONITOR:
        f = cfg["fuentes"][fuente]
        copia = aterrizar(origen / f["ruta"], almacen.carpeta("aterrizaje", fuente, lote_id))
        crudo = leer_origen(Path(copia["archivo"]), f["formato"])
        std = estandarizar_sos(crudo, f, series) if fuente == "sos" else estandarizar_vims(crudo, fuente, f, series)
        std = asignar_vida(std, cambios)
        nombre = TABLA_DE_FUENTE[fuente]
        previo = almacen.leer(nombre)
        n_previo = 0 if previo is None else len(previo)
        tabla, resumen = fusionar(previo, std, fecha_lote, tipo, f["desfase_disponible_dias"],
                                  f["ventana_relectura_dias"], lote_id)
        agregar = tabla.iloc[n_previo:]
        if len(agregar) or previo is None:
            almacen.escribir(nombre, agregar, modo="append")
        info = {"origen": copia, **resumen, "calidad": reporte_calidad(tabla, fuente, series, fecha_lote)}
        reporte["fuentes"][fuente] = info
        filas_lote.append(_fila_lote(lote_id, tipo, fecha_lote, fuente, info))

    # Bitácora de lotes (re-ejecutar un lote reemplaza sus filas) y reporte del lote.
    lotes = almacen.leer("ingesta_lotes")
    lotes = pd.DataFrame(filas_lote) if lotes is None else pd.concat(
        [lotes[lotes["lote_id"] != lote_id], pd.DataFrame(filas_lote)], ignore_index=True)
    almacen.escribir("ingesta_lotes", lotes, modo="overwrite")
    almacen.archivos("reportes", f"{lote_id}.json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return reporte


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fecha", type=date.fromisoformat, default=date.today())
    ap.add_argument("--tipo", choices=["diario", "historico"], default="diario")
    ap.add_argument("--origen", default=os.environ.get("INGESTA_ORIGEN"))
    ap.add_argument("--destino", default=os.environ.get("INGESTA_DESTINO"), help="raíz del Lakehouse de entrada")
    ap.add_argument("--formato", choices=["parquet", "delta"], default=os.environ.get("INGESTA_FORMATO", "parquet"))
    a = ap.parse_args(argv)
    if not a.origen or not a.destino:
        ap.error("faltan --origen/--destino (o INGESTA_ORIGEN/INGESTA_DESTINO)")
    rep = ejecutar(a.fecha, a.tipo, Path(a.origen), Path(a.destino), formato=a.formato)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
