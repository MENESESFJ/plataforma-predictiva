# Plan del piloto DMH 798AC

Propuesta para el kickoff. Las fechas cuentan desde un inicio propuesto (lunes 7 de diciembre de 2026) y se ajustan
en el kickoff.

- **Carta Gantt interactiva:** https://claude.ai/artifact/Nb4gmcBYwuVPehQHCdKeBs
- **CSV para Excel o MS Project:** `docs/gestion/plan_piloto_dmh.csv` (separador `;`, 25 tareas y 5 hitos con inicio,
  fin, dependencias, insumos, entregable y ruta crítica)
- **Fuente del plan:** `herramientas/gestion/generar_plan.py`. Para mover todo el plan se cambia la fecha de inicio;
  para ajustar una tarea, su fila. El script regenera el CSV.

## Hitos

| Hito | Fecha | Semana |
|---|---|---|
| H0 · Kickoff | 11 dic 2026 | 1 |
| H1 · Cierre del caso de uso (gate Fase 0) | 15 ene 2027 | 6 |
| H2 · Monitor VIMS y aceite en piloto con Monitoreo de Condiciones | 12 mar 2027 | 14 |
| H3 · Modelo predictivo aprobado (gate Fase 3) | 28 may 2027 | 25 |
| H4 · Decisión de escalamiento a la flota | 4 jun 2027 | 26 |

## Frentes de trabajo

| Frente | Tareas | Semanas |
|---|---|---|
| Gobierno | Kickoff; seguimiento semanal | 1–26 |
| Cierre del caso de uso | Validar los 14 cambios; 4 causas raíz; 2 modos FMEA nuevos; métrica y presupuesto de alertas | 2–6 |
| Datos y plataforma | Copia del histórico DMH; workspaces Fabric y Azure ML; Cat Inspect; particulado histórico; rangos y unidades VIMS | 1–9 |
| Monitor de desviaciones | Ingesta; comparaciones y semáforo; prueba hacia atrás; lista diaria; piloto y calibración; particulado y rellenos | 4–19 |
| Interpretación con IA | Prueba 4 (salida estructurada); entorno corporativo; triage y especialistas | 4–19 |
| Modelo predictivo | Modelo de degradación; validación con los 14 eventos | 20–25 |
| Operación del piloto | Tablero Power BI; revisión semanal; evaluación y escalamiento | 16–26 |

## Ruta crítica

Copia del histórico (D1) → ingesta (M1) → comparaciones y semáforo (M2) → prueba hacia atrás (M3) → piloto con
Monitoreo de Condiciones (M5) → modelo (P1) → validación (P2) → evaluación (O3). No tiene holgura.

## Insumos de otros equipos (con fecha límite)

| Equipo | Qué entrega | Fecha límite | Ruta crítica |
|---|---|---|---|
| TI / Datos | Copia del histórico DMH desde 2023 | 25 dic 2026 | Sí |
| Confiabilidad + Ingeniería | Listado de los 14 cambios validado | 1 ene 2027 | No (es predecesor de M3) |
| Centro Técnico | 4 causas raíz pendientes | 8 ene 2027 | No |
| Monitoreo de Condiciones + Confiabilidad | Métrica de éxito y alertas por semana | 8 ene 2027 | No |
| TI / Datos | Acceso a Cat Inspect | 8 ene 2027 | No |
| Monitoreo de Condiciones | Rangos y unidades VIMS | 8 ene 2027 | No (es predecesor de M2) |
| Confiabilidad | FMEA v1.1 con los 2 modos nuevos | 15 ene 2027 | No |
| TI / Plataforma | Workspaces de Fabric y Azure ML | 22 ene 2027 | No |
| Monitoreo de Condiciones + Datos | Particulado histórico unificado | 5 feb 2027 | No |
| TI / Plataforma | Entorno de IA corporativo | 5 mar 2027 | No |
| Monitoreo de Condiciones + Desarrollo | Umbrales calibrados en el piloto | 16 abr 2027 | Sí |
| Confiabilidad + Desarrollo | Modelo aprobado | 28 may 2027 | Sí |

## Supuestos y riesgos de plazo

- Si el kickoff se corre, el plan se desplaza igual.
- La copia del histórico es lo más urgente: Databricks se retira en 2027 sin fecha definida.
- Fiestas y vacaciones de verano (diciembre a febrero) reducen la disponibilidad de los equipos técnicos.
- El piloto se calibra a las alertas por semana que Monitoreo de Condiciones puede revisar.
- El acceso a la VM de Azure dura hasta ~mayo de 2027 y la versión de gpt-5 usada se retira el 8 de febrero de 2027.
- La dedicación en horas por equipo no está estimada; se acuerda en el kickoff.
- El escalamiento a otros contratos 798AC y a 797B/F queda fuera de este horizonte y se planifica con el hito H4.
