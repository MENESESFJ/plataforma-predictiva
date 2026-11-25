"""Ingesta del monitor (DP-010): alcance, calidad, vida de motor, versiones y regla de corte. Datos sintéticos."""
from datetime import date

import pandas as pd
import pytest

from ingesta import monitor as im

CFG = im.cargar_config()
SERIES = im.series_flota(CFG)
MH340, MH341 = "SKH00615", "SKH00614"
MOTOR = "1000.00.CC.0 MOTOR"


def _tendencias(filas):
    return pd.DataFrame(filas, columns=["Fecha", "SerialNumber", "Equipo", "Componente", "Tendencia",
                                        "Condition", "CountTrend", "AverageTrend"]).astype(str)


def _std(filas):
    return im.estandarizar_vims(_tendencias(filas), "vims_tendencias", CFG["fuentes"]["vims_tendencias"], SERIES)


def test_alcance_solo_flota_y_motor():
    t = _std([["2027-01-10", MH340, "MH-340", MOTOR, "Engine Oil Pressure", "Engine Running", "12", "410"],
              ["2027-01-10", "TKD00144", "TKD144", MOTOR, "Engine Oil Pressure", "Engine Running", "12", "400"],
              ["2027-01-10", MH340, "MH340", "4050.00.CC.0 MANDO FINAL", "x", "Engine Running", "12", "1"]])
    assert len(t) == 1 and t.loc[0, "equipo"] == "MH340"  # código de equipo desde la serie, no del origen


def test_centinela_y_pocas_lecturas_se_marcan_sin_borrar():
    t = _std([["2027-01-10", MH340, "MH340", MOTOR, "Left Exhaust Temperature", "Engine Running", "12", "-3277.4"],
              ["2027-01-10", MH340, "MH340", MOTOR, "Engine Oil Pressure", "Engine Running", "1", "410"]])
    assert len(t) == 2 and not t["valido"].any()
    assert set(t["motivo"]) == {"centinela", "pocas_lecturas"}


def test_sos_csv_envuelto_formato_largo(tmp_path):
    cab = '"Numero Serie","Id Lab.",Componente,"Fecha Muestra","Horas Maquina","Horas Aceite","Cambio Aceite",SampleComment,Fe,Cu,Pb,Si,Na,K,PQI,St,V100'
    fila = f'{MH340},R1-526001-1,ENG,2027-01-05,0,250,N,"Hierro, leve",40,5,3,8,2,1,20,0.3,14.1'
    ruta = tmp_path / "sos.csv"
    ruta.write_text("\n".join('"' + l.replace('"', '""') + '"' for l in [cab, fila]), encoding="utf-8")
    t = im.estandarizar_sos(im.leer_origen(ruta, "csv_envuelto"), CFG["fuentes"]["sos"], SERIES)
    assert len(t) == len(CFG["fuentes"]["sos"]["parametros"])
    fe = t[t["parametro"] == "Fe"].iloc[0]
    assert fe["valor"] == 40 and fe["comentario"] == "Hierro, leve" and fe["motivo"] == "horometro_cero"
    tabla, _ = im.fusionar(None, t, date(2027, 1, 20), "historico", 3, 60, "l1")
    assert (tabla["fecha_disponible"] == pd.Timestamp("2027-01-08")).all()  # muestra + 3 días


def test_vida_de_motor_se_reinicia_con_el_cambio():
    t = _std([["2027-01-09", MH340, "MH340", MOTOR, "Engine Oil Pressure", "Engine Running", "12", "410"],
              ["2027-01-10", MH340, "MH340", MOTOR, "Engine Oil Pressure", "Engine Running", "12", "300"],
              ["2027-01-10", MH341, "MH341", MOTOR, "Engine Oil Pressure", "Engine Running", "12", "400"]])
    cambios = pd.DataFrame({"serie_equipo": [MH340], "fecha_cambio": [pd.Timestamp("2027-01-10")]})
    t = im.asignar_vida(t, cambios)
    assert list(t["vida_motor"]) == ["MH340-v0", "MH340-v1", "MH341-v0"]


def test_dato_atrasado_y_correccion_respetan_el_corte():
    fila = ["2027-01-10", MH340, "MH340", MOTOR, "Engine Oil Pressure", "Engine Running", "12"]
    t1, r1 = im.fusionar(None, _std([fila + ["410"]]), date(2027, 1, 11), "diario", 1, 15, "l1")
    assert r1["nuevas"] == 1 and t1.loc[0, "fecha_disponible"] == pd.Timestamp("2027-01-11")
    # mismo lote otra vez: idempotente
    t1b, r1b = im.fusionar(t1, _std([fila + ["410"]]), date(2027, 1, 11), "diario", 1, 15, "l1")
    assert r1b["sin_cambio"] == 1 and len(t1b) == 1
    # el origen corrige el valor días después: versión nueva, la anterior se conserva
    t2, r2 = im.fusionar(t1, _std([fila + ["390"]]), date(2027, 1, 14), "diario", 1, 15, "l2")
    assert r2["corregidas"] == 1 and len(t2) == 2
    assert im.vista_al_corte(t2, date(2027, 1, 12)).loc[0, "valor"] == 410  # lo que se sabía el 12
    assert im.vista_al_corte(t2, date(2027, 1, 14)).loc[0, "valor"] == 390
    assert im.vista_al_corte(t2, date(2027, 1, 10)).empty                 # antes de llegar, no existe
    # un dato de hace un mes que aparece hoy queda fuera de la ventana de relectura
    viejo = ["2026-12-01"] + fila[1:] + ["405"]
    _, r3 = im.fusionar(t2, _std([viejo]), date(2027, 1, 14), "diario", 1, 15, "l3")
    assert r3["fuera_de_ventana"] == 1 and r3["nuevas"] == 0


def test_ejecucion_completa(tmp_path):
    origen, destino = tmp_path / "lake", tmp_path / "proyecto"
    f = CFG["fuentes"]
    for clave, contenido in {
        "vims_tendencias": _tendencias([["2027-01-10", MH340, "MH340", MOTOR, "Engine Oil Pressure",
                                         "Engine Running", "12", "410"]]).to_csv(index=False),
        "vims_eventos": f"Date,SerialNumber,Equipo,EventName,Componente,EventSeverity,EventDuration\n"
                        f"2027-01-10,{MH340},MH340,Low Engine Oil Level,{MOTOR},2,30\n",
        "sos": '"""Numero Serie"",""Id Lab."",Componente,""Fecha Muestra"",""Horas Maquina"",""Horas Aceite"",""Cambio Aceite"",SampleComment,Fe"\n'
               f'"{MH340},R1,ENG,2027-01-05,13000,250,N,ok,40"\n',
        "cambios_motor": "Contrato;FechaCambio;SerialNumber;Componentes\nMinistro Hales;01/06/2026;SKH00615;motor\n",
    }.items():
        ruta = origen / f[clave]["ruta"]
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")
    rep = im.ejecutar(date(2027, 1, 11), "diario", origen, destino, CFG)
    vims = rep["fuentes"]["vims_tendencias"]
    assert vims["nuevas"] == 1 and len(vims["origen"]["sha256"]) == 64
    assert "MH340" not in vims["calidad"]["equipos_sin_datos_dia_analizado"]
    assert "MH341" in vims["calidad"]["equipos_sin_datos_dia_analizado"]  # sin datos se informa, no es normal
    assert rep["fuentes"]["vims_eventos"]["nuevas"] == 1 and rep["fuentes"]["sos"]["nuevas"] == 1
    tabla = pd.read_parquet(destino / "entrada/estandar/vims_tendencias.parquet")
    assert tabla.loc[0, "vida_motor"] == "MH340-v1"
    assert (destino / "entrada/reportes/20270111-diario.json").exists()
