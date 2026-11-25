# Gobierno del piloto DMH 798AC

Cómo se revisa, decide y cierra lo que entrega la plataforma, quién hace qué y qué se le pide a TI. Complementa el plan
(`plan_piloto_dmh.md`) y las decisiones (`docs/fase0/decisiones_proyecto.md`). Los roles, estados y plazos de este
documento son una **propuesta que se ratifica en el kickoff** (tarea G1) y se cierra con Monitoreo de Condiciones e
Ingeniería de Mantenimiento (tarea G3).

## 1. Principio rector

**El monitor detecta; el FMEA contextualiza; el especialista confirma; Mantenimiento decide; la ejecución y el hallazgo
cierran el aprendizaje.**

La plataforma recomienda. No reemplaza el criterio técnico, no crea avisos ni órdenes de trabajo por sí sola y no se
reentrena sin aprobación.

## 2. Reglas de diseño

| Regla | Dónde queda en el proyecto |
|---|---|
| Ningún dato posterior a la fecha de corte influye en una evaluación | Fechas de disponibilidad por fuente en `data_contract.yaml` (SOS a fecha de muestra + 3 días; Cat Inspect a DateClosed) |
| Falta de datos no es condición normal | Estado "sin datos" del semáforo (`monitor_desviaciones.md`, sección 8) |
| Un baseline de desarrollo nunca se presenta como modelo aprobado | DP-007: la salida lleva una advertencia visible |
| Un modo FMEA sin variable observable se declara no observable | DP-009 |
| AFA/RCA y el informe de taller son etiquetas, nunca predictores | `data_contract.yaml` |
| Entrenamiento y operación separados; promover un modelo requiere aprobación y es reversible | Registro de modelos con alias candidato / vigente |
| Toda salida registra la versión de datos, reglas, modelo y FMEA | Trazabilidad por ejecución |
| Las fallas de fuente y los datos insuficientes son visibles para el usuario | Calidad de datos antes de comparar (`monitor_desviaciones.md`, sección 4) |

## 3. Ciclo de un caso

Un caso nace cuando un camión entra en alerta en la lista diaria del monitor. **Una alerta repetida actualiza el caso
abierto; no crea otro.**

| Estado | Quién lo define | Significado |
|---|---|---|
| Pendiente | Monitor (automático) | Alerta nueva, sin revisar |
| En observación | Monitoreo de Condiciones | Desviación real sin acción inmediata; se sigue en los próximos días |
| Requiere información | Monitoreo de Condiciones | Falta una muestra, inspección o dato para decidir |
| Confirmada | Monitoreo de Condiciones | Condición real que requiere acción |
| Descartada | Monitoreo de Condiciones | No es una condición real; se registra el motivo (insumo para calibrar) |
| Escalada | Ingeniería de Mantenimiento | Acción definida, con prioridad, plazo y criterio de cierre |
| Cerrada | Ingeniería de Mantenimiento | Hay evidencia de resolución (hallazgo registrado) o un descarte técnico documentado |

Cada cambio de estado registra quién, cuándo y por qué. En el piloto los casos se llevan en una tabla simple; la
integración con avisos y órdenes de trabajo de SAP queda para la operación (DP-008).

### Plazos de revisión propuestos (por validar con Monitoreo de Condiciones)

| Prioridad | Plazo de revisión |
|---|---|
| Crítica | Mismo turno |
| Alta | 24 horas |
| Media | 3 días hábiles |
| Observación | Próxima revisión semanal |

## 4. Responsables

R = ejecuta · A = aprueba · C = consultado · I = informado.

| Actividad | Desarrollo | Confiabilidad | Monitoreo de Condiciones | Ingeniería de Mantenimiento | Centro Técnico | Planificación | TI |
|---|---|---|---|---|---|---|---|
| Integrar fuentes de datos | R | C | C | I | I | I | A/C |
| Validar eventos y causas raíz | C | A/R | C | C | R | I | I |
| Aprobar FMEA y modos nuevos | C | A/R | C | C | C | I | I |
| Construir monitor, variables y modelos | A/R | C | C | I | I | I | C |
| Revisar alertas de la lista diaria | C | C | A/R | C | I | I | I |
| Definir la acción | I | C | C | A/R | C | C | I |
| Planificar y ejecutar | I | I | C | C | I | A/R | I |
| Registrar el hallazgo | C | C | R | R | C | A/R | I |
| Promover un modelo o regla a vigente | R | A | C | C | I | I | C |
| Operar la infraestructura | C | I | I | I | I | I | A/R |

## 5. Entregables mínimos para salir del piloto

| Entregable | Responsable | Tarea del plan |
|---|---|---|
| Listado de los 14 eventos validado | Confiabilidad | F01, F02 |
| FMEA v1.1 aprobado, con modos no observables marcados | Confiabilidad | F03 |
| Métrica de éxito y presupuesto de alertas | Monitoreo de Condiciones + Confiabilidad | F04 |
| Tabla de vidas de motor (equipo, serie, instalación, retiro, horas, motivo) | Confiabilidad + Componentes | D6 |
| Diccionario de variables y cobertura por camión y variable | Desarrollo + dueños de fuentes | D7 |
| Procedimiento de revisión de casos | Monitoreo de Condiciones + Ingeniería de Mantenimiento | G3 |
| Prueba hacia atrás reproducible (point-in-time) | Desarrollo + Confiabilidad | M3 |
| Catálogo de acciones por modo y severidad, con criterio de cierre | Ingeniería de Mantenimiento | Antes de P2 |

## 6. Requerimientos a TI

Se pide una plataforma segura y gobernada, no una máquina para ejecutar Python.

| Capa | Propuesta | Para el piloto |
|---|---|---|
| Datos | Microsoft Fabric | Workspace del proyecto (D2); DEV y PROD separados antes de operar |
| Modelos | Azure Machine Learning + MLflow | Workspace (D2); alias candidato / vigente |
| IA | Azure AI Foundry corporativo | A2 |
| Identidad | Microsoft Entra ID | Grupos por rol, mínimo privilegio, identidades administradas |
| Secretos | Azure Key Vault o estándar corporativo | Credenciales fuera del código y de los notebooks |
| Código | Repositorio corporativo (GitHub Enterprise o Azure DevOps) | Migrar el repositorio actual; ramas protegidas, revisión y pruebas automáticas |
| Estado y casos | Base operacional administrada (Azure SQL o equivalente) | En el piloto, tabla en Fabric; SQLite solo para desarrollo local |
| Visualización | Power BI | Tablero del piloto (O1) |
| Monitoreo | Azure Monitor / monitoreo de Fabric | Fallas de carga, atrasos, camiones sin datos, casos vencidos |
| Continuidad | Procedimiento TI | Respaldo, recuperación y soporte antes de operar |

## 7. Regla de avance

No se avanza al siguiente hito solo porque el software funciona. Cada hito requiere evidencia y la aceptación del área
dueña del riesgo: Confiabilidad para eventos y FMEA, Monitoreo de Condiciones para la carga de revisión, TI para la
plataforma.

## 8. Fuera del piloto (para la operación)

- Integración automática de casos con avisos y órdenes de trabajo de SAP.
- Fuentes adicionales: ECM (códigos y snapshots), reportes de servicio (PSR), SAP / AMT para separar trabajo ya
  programado. Se evalúan con el hito H4.
- Ambiente de pruebas (TEST) separado, CI/CD con despliegue y plan de continuidad completo.
