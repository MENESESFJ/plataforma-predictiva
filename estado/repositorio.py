"""Persistencia del Estado global: una fila por request_id con el Estado serializado."""
import sqlite3
from typing import Optional

from contratos.base import Estado


class RepositorioEstado:
    def __init__(self, ruta: str = ":memory:") -> None:
        self._con = sqlite3.connect(ruta)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS estado ("
            " request_id TEXT PRIMARY KEY, version_contrato TEXT NOT NULL,"
            " fase TEXT NOT NULL, cerrado INTEGER NOT NULL, estado_json TEXT NOT NULL)")

    def guardar(self, est: Estado) -> None:
        with self._con:
            self._con.execute(
                "INSERT INTO estado VALUES (?, ?, ?, ?, ?) ON CONFLICT(request_id) DO UPDATE SET"
                " version_contrato=excluded.version_contrato, fase=excluded.fase,"
                " cerrado=excluded.cerrado, estado_json=excluded.estado_json",
                (est.request_id, est.version_contrato, est.fase.value, int(est.cerrado),
                 est.model_dump_json()))

    def cargar(self, request_id: str) -> Optional[Estado]:
        fila = self._con.execute(
            "SELECT estado_json FROM estado WHERE request_id = ?", (request_id,)).fetchone()
        return Estado.model_validate_json(fila[0]) if fila else None

    def existe(self, request_id: str) -> bool:
        return self._con.execute(
            "SELECT 1 FROM estado WHERE request_id = ?", (request_id,)).fetchone() is not None
