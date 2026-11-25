"""Fuente única del plan del piloto: genera el CSV (Excel / MS Project) y el JSON para la Gantt.

Uso: python herramientas/gestion/generar_plan.py docs/gestion/plan_piloto_dmh.csv plan.json
Para mover el plan, cambiar INICIO; para ajustar una tarea, editar su fila en T.
"""
import csv
import json
import sys
from datetime import date, timedelta

INICIO = date(2026, 12, 7)  # lunes de la semana 1 (propuesta)

# id, frente, tarea, responsable, sem_inicio, duracion_sem, depende_de, insumos, entregable, critica
T = [
    ("G1", "Gobierno", "Kickoff y acuerdo de alcance, roles y cadencia", "Líder del proyecto", 1, 1, "",
     "Presentación de avance; ficha del caso de uso", "Acta de kickoff y matriz de responsables", True),
    ("G2", "Gobierno", "Seguimiento semanal del plan", "Líder del proyecto + PMO", 2, 25, "G1",
     "Este plan", "Minuta y estado semanal", False),
    ("G3", "Gobierno", "Proceso de revisión de casos: estados, plazos, responsables y cierre", "Monitoreo de Condiciones + Ingeniería de Mantenimiento", 8, 3, "F04",
     "Lista diaria de ejemplo; propuesta de estados y plazos (gobierno_piloto.md)", "Procedimiento de revisión de casos acordado", False),
    ("F01", "Cierre del caso de uso", "Validar el modo de falla de los 14 cambios de motor", "Confiabilidad + Ingeniería", 2, 3, "G1",
     "Listado de eventos; resultados de los agentes", "Listado de eventos validado", True),
    ("F02", "Cierre del caso de uso", "Completar las 4 causas raíz pendientes", "Centro Técnico", 2, 4, "G1",
     "Plantilla de falla de componentes (SharePoint); informes de desarme", "Causas raíz en el listado", False),
    ("F03", "Cierre del caso de uso", "Decidir los 2 modos FMEA nuevos", "Confiabilidad", 5, 2, "F01",
     "Propuesta de modos (bloqueo hidráulico, tren de distribución)", "FMEA v1.1 aprobado", False),
    ("F04", "Cierre del caso de uso", "Acordar métrica de éxito y presupuesto de alertas", "Monitoreo de Condiciones + Confiabilidad", 3, 3, "G1",
     "Diseño del monitor; estimación de costos", "Métrica y alertas por semana acordadas", False),
    ("D1", "Datos y plataforma", "Copia del histórico DMH desde 2023", "TI / Datos", 1, 3, "",
     "Acceso de lectura al lake (VIMS, aceite, rellenos, cambios)", "Dataset histórico propio del proyecto", True),
    ("D2", "Datos y plataforma", "Workspace de Fabric y de Azure ML del proyecto", "TI / Plataforma", 2, 6, "",
     "Aprobación y licencias", "Workspaces habilitados", False),
    ("D3", "Datos y plataforma", "Acceso de lectura a Cat Inspect", "TI / Datos", 2, 4, "",
     "Conexión a SQL Server o extracto periódico", "Particulado actual disponible", False),
    ("D4", "Datos y plataforma", "Particulado histórico de Argos y equivalencia de escalas", "Monitoreo de Condiciones + Datos", 6, 4, "D1, D3",
     "Escala de Argos; severidad por color de Cat Inspect", "Serie de particulado unificada", False),
    ("D5", "Datos y plataforma", "Rangos físicos y unidades de los parámetros VIMS", "Monitoreo de Condiciones", 3, 3, "G1",
     "Diccionario de tendencias", "Tabla de rangos y unidades", False),
    ("D6", "Datos y plataforma", "Tabla de vidas de motor: equipo, serie, instalación, retiro, horas y motivo", "Confiabilidad + Componentes", 2, 3, "G1",
     "Base de cambios de componentes; planilla de fallas", "Tabla de vidas de motor validada", False),
    ("D7", "Datos y plataforma", "Diccionario de variables y cobertura por camión y variable", "Desarrollo + dueños de las fuentes", 4, 2, "D1",
     "Histórico copiado; catálogos de VIMS y aceite", "Diccionario con unidades y cobertura medida", False),
    ("M1", "Monitor de desviaciones", "Ingesta real y calidad de datos", "Desarrollo", 4, 3, "D1",
     "Contrato de datos; mecanismo de ingesta (DP-010)", "Ingesta validada con datos DMH", True),
    ("M2", "Monitor de desviaciones", "Comparaciones y semáforo: VIMS y aceite", "Desarrollo", 7, 4, "M1, D5, D6, D7",
     "Diseño del monitor (DP-006)", "Tablas diarias de desviaciones y estado", True),
    ("M3", "Monitor de desviaciones", "Prueba hacia atrás con las 10 fallas y falsas alarmas", "Desarrollo + Confiabilidad", 11, 3, "M2, F01",
     "Eventos validados", "Informe: anticipación y falsas alarmas", True),
    ("M4", "Monitor de desviaciones", "Lista diaria de revisión para Monitoreo de Condiciones", "Desarrollo", 11, 2, "M2, D2",
     "Presupuesto de alertas; herramientas que usa el equipo", "Lista diaria (Power BI o correo)", False),
    ("M5", "Monitor de desviaciones", "Piloto con Monitoreo de Condiciones y calibración", "Monitoreo de Condiciones + Desarrollo", 14, 6, "M3, M4, G3",
     "Revisión de las primeras listas", "Umbrales calibrados", True),
    ("M6", "Monitor de desviaciones", "Sumar particulado y rellenos", "Desarrollo", 15, 3, "M2, D4",
     "Serie de particulado unificada; rellenos", "Monitor completo (etapa 2)", False),
    ("A1", "Interpretación con IA", "Prueba 4: salida estructurada por agente", "Desarrollo", 4, 3, "",
     "VM de Azure (acceso hasta ~mayo 2027)", "Resultados y conclusiones de la prueba 4", False),
    ("A2", "Interpretación con IA", "Entorno de IA corporativo (Azure AI Foundry)", "TI / Plataforma", 6, 8, "",
     "Disponibilidad corporativa desde 2027", "Proyecto y modelo desplegados", False),
    ("A3", "Interpretación con IA", "Triage y especialistas sobre alertas reales", "Desarrollo", 16, 4, "H2, A1, A2",
     "Alertas del piloto", "Casos explicados para la revisión semanal", False),
    ("P1", "Modelo predictivo", "Variables y modelo de degradación con datos reales", "Desarrollo", 20, 4, "M5",
     "Reproceso histórico del monitor; etiquetas por vida de motor (ciclo de aprendizaje, DP-011)", "Modelo candidato registrado", True),
    ("P2", "Modelo predictivo", "Validación contra los 14 eventos y aprobación", "Confiabilidad + Desarrollo", 24, 2, "P1",
     "Listado validado; métrica de éxito; criterios del validador (DP-011)", "Modelo vigente aprobado", True),
    ("O1", "Operación del piloto", "Tablero Power BI del piloto", "Desarrollo + BI", 17, 4, "M4, D2",
     "Tablas de estado y desviaciones", "Tablero en uso", False),
    ("O2", "Operación del piloto", "Revisión semanal de casos con especialistas", "Monitoreo de Condiciones + Confiabilidad", 16, 10, "H2",
     "Lista diaria; casos explicados", "Registro de decisiones", False),
    ("O3", "Operación del piloto", "Evaluación del piloto y propuesta de escalamiento", "Líder del proyecto + PMO", 26, 1, "P2, O2",
     "Métricas del piloto; costos", "Informe y decisión de escalamiento", True),
]

H = [  # id, hito, semana (fin), depende
    ("H0", "Kickoff", 1, "G1"),
    ("H1", "Cierre del caso de uso (gate Fase 0)", 6, "F01, F02, F03, F04"),
    ("H2", "Monitor VIMS y aceite en piloto con Monitoreo de Condiciones", 14, "M3, M4"),
    ("H3", "Modelo predictivo aprobado (gate Fase 3)", 25, "P2"),
    ("H4", "Decisión de escalamiento a la flota", 26, "O3"),
]


def lunes(sem):
    return INICIO + timedelta(weeks=sem - 1)


def viernes(sem):
    return lunes(sem) + timedelta(days=4)


def main(csv_path, json_path):
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Frente", "Tarea", "Responsable", "Inicio", "Fin", "Semana inicio", "Duración (semanas)",
                    "Depende de", "Insumos", "Entregable", "Ruta crítica", "Tipo"])
        for t in T:
            i, fr, ta, re, s, d, de, ins, en, cr = t
            w.writerow([i, fr, ta, re, lunes(s).isoformat(), viernes(s + d - 1).isoformat(), s, d, de, ins, en,
                        "Sí" if cr else "No", "Tarea"])
        for i, n, s, de in H:
            w.writerow([i, "Hito", n, "", viernes(s).isoformat(), viernes(s).isoformat(), s, 0, de, "", "", "", "Hito"])
    datos = {"inicio": INICIO.isoformat(), "semanas": 26,
             "tareas": [dict(zip(["id", "frente", "tarea", "responsable", "s", "d", "depende", "insumos", "entregable", "critica"], t))
                        for t in T],
             "hitos": [dict(zip(["id", "nombre", "s", "depende"], h)) for h in H]}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    print(len(T), "tareas,", len(H), "hitos; fin", viernes(26))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
