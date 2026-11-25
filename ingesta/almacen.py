"""Dónde lee y escribe la ingesta, sin depender de la plataforma (DP-005, DP-012).

- Local o lake actual: tablas Parquet en <destino>/Tables/<tabla>.parquet.
- Fabric: tablas Delta del Lakehouse en <destino>/Tables/<tabla> (con `deltalake`, incluido en Fabric).
  <destino> es la raíz del Lakehouse: /lakehouse/default en un notebook con Lakehouse por defecto, o su
  ruta abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>.Lakehouse.

Los archivos (copias de origen y reportes) van en <destino>/Files/, igual que en un Lakehouse.
"""
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from ingesta.esquemas import a_pandas, conformar


class Almacen:
    def __init__(self, raiz: Path, formato: Optional[str] = None):
        self.raiz = Path(raiz)
        self.formato = formato or os.environ.get("INGESTA_FORMATO", "parquet")
        if self.formato not in ("parquet", "delta"):
            raise ValueError(f"formato no soportado: {self.formato}")

    # --- archivos ---------------------------------------------------------------------------------
    def carpeta(self, *partes: str) -> Path:
        ruta = self.raiz / "Files" / Path(*partes)
        ruta.mkdir(parents=True, exist_ok=True)
        return ruta

    def archivos(self, *partes: str) -> Path:
        ruta = self.raiz / "Files" / Path(*partes)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        return ruta

    # --- tablas -----------------------------------------------------------------------------------
    def _ruta_tabla(self, tabla: str) -> Path:
        return self.raiz / "Tables" / (f"{tabla}.parquet" if self.formato == "parquet" else tabla)

    def existe(self, tabla: str) -> bool:
        return self._ruta_tabla(tabla).exists()

    def leer(self, tabla: str) -> Optional[pd.DataFrame]:
        if not self.existe(tabla):
            return None
        if self.formato == "parquet":
            return a_pandas(pd.read_parquet(self._ruta_tabla(tabla)), tabla)
        from deltalake import DeltaTable
        return a_pandas(DeltaTable(str(self._ruta_tabla(tabla))).to_pyarrow_dataset().to_table().to_pandas(), tabla)

    def escribir(self, tabla: str, df: pd.DataFrame, modo: str = "overwrite") -> None:
        """modo: overwrite (reemplaza la tabla) o append (agrega filas)."""
        df = conformar(df, tabla)
        ruta = self._ruta_tabla(tabla)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if self.formato == "parquet":
            if modo == "append" and ruta.exists():
                df = pd.concat([conformar(self.leer(tabla), tabla), df], ignore_index=True)
            df.to_parquet(ruta, index=False)
            return
        from deltalake import write_deltalake
        write_deltalake(str(ruta), df, mode=modo)
