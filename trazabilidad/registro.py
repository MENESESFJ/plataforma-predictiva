"""Registro append-only de trazas de ejecución (una fila por paso de agente)."""
import sqlite3
from typing import List

from contratos.agentes import RegistroAuditoria


class RegistroTrazas:
    def __init__(self, ruta: str = ":memory:") -> None:
        self._con = sqlite3.connect(ruta)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS traza ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,"
            " agente TEXT NOT NULL, estado TEXT NOT NULL, registro_json TEXT NOT NULL)")
        self._con.execute("CREATE INDEX IF NOT EXISTS ix_traza_run ON traza(run_id)")

    def registrar(self, registro: RegistroAuditoria) -> None:
        with self._con:
            self._con.execute(
                "INSERT INTO traza (run_id, agente, estado, registro_json) VALUES (?, ?, ?, ?)",
                (registro.run_id, registro.agente, registro.estado.value,
                 registro.model_dump_json()))

    def por_run(self, run_id: str) -> List[RegistroAuditoria]:
        filas = self._con.execute(
            "SELECT registro_json FROM traza WHERE run_id = ? ORDER BY id", (run_id,))
        return [RegistroAuditoria.model_validate_json(f[0]) for f in filas]
