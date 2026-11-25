# Fabric notebook: nb_ingesta_monitor
#
# Plantilla del notebook de Fabric que ejecuta la ingesta diaria del monitor (DP-010, DP-012).
# Se importa a Fabric como notebook de Python (cada bloque "# %%" es una celda).
#
# Requisitos en el workspace (ver docs/arquitectura/fabric_estructura.md):
# - Lakehouse por defecto del notebook: lh_pp_entrada.
# - Acceso directo (shortcut) en lh_pp_entrada/Files/origen al lake actual (solo lectura).
# - Entorno de Fabric con el paquete del proyecto (wheel de plataforma-predictiva) y deltalake.
# - El listado de eventos validado se lee del paquete (docs/fase0); cuando viva en Fabric, se cambia la ruta.

# %% [parameters]
# Celda de parámetros: el pipeline de Fabric los sobrescribe en cada ejecución.
fecha_lote = ""          # vacío = hoy (zona horaria del pipeline)
tipo = "diario"          # "historico" solo para la carga inicial (D1)

# %%
from datetime import date
from pathlib import Path

from ingesta.monitor import ejecutar

ORIGEN = Path("/lakehouse/default/Files/origen")   # shortcut al lake actual (bronze/ y silver/)
DESTINO = Path("/lakehouse/default")               # raíz del Lakehouse de entrada (Files/ y Tables/)

fecha = date.fromisoformat(fecha_lote) if fecha_lote else date.today()
reporte = ejecutar(fecha, tipo, ORIGEN, DESTINO, formato="delta")

# %%
# Resumen para el historial de ejecuciones y para decidir si el pipeline avisa.
atrasadas = [f for f, r in reporte["fuentes"].items() if r["calidad"]["atrasada"]]
resumen = {
    "lote_id": reporte["lote_id"],
    "nuevas": {f: r["nuevas"] for f, r in reporte["fuentes"].items()},
    "fuentes_atrasadas": atrasadas,
    "cambios_motor_nuevos": reporte["eventos_pendientes"]["nuevos"],
}
print(resumen)

# %%
# Valor de salida para el pipeline: si hay fuentes atrasadas o cambios de motor nuevos, el pipeline
# envía el aviso (Teams o correo) a Desarrollo y a Confiabilidad.
try:
    import notebookutils  # disponible solo dentro de Fabric
    import json
    notebookutils.notebook.exit(json.dumps(resumen))
except ImportError:
    pass
