# Ficha de Caso de Uso – Falla mayor de motor CAEX

| | |
|---|---|
| Versión | 0.1 (borrador) |
| Estado | En construcción – requiere firma de Confiabilidad y Data Analytics (gate Fase 0) |
| Componente | `motor_diesel` |
| Roadmap | Etapa 1, Fase 0 |

Convención: ✅ definido · 🟡 propuesto, falta validar · ⬜ por definir.

---

## 1. Unidad de análisis

| Campo | Valor | Estado |
|---|---|---|
| Unidad | Equipo-componente: un motor instalado en un camión, durante su ciclo de vida (instalación → retiro) | 🟡 |
| Flota piloto | 798AC o 797F (ver sección 7) | ⬜ |
| Modelos cubiertos por el conocimiento | 793F, 794AC, 797F y 798AC; el 798AC por equivalencia con 793F/797F (DEC-001) | ✅ |

## 2. Evento objetivo

| Campo | Valor | Estado |
|---|---|---|
| Evento | Falla mayor de motor (`falla_mayor_motor`) | 🟡 |
| Criterio de identificación | Órdenes de trabajo con códigos de falla mayor de motor | ⬜ Códigos por confirmar en SAP/Maximo (`definition.json`) |
| Modos de falla cubiertos | 8 modos predictivos aprobados (MFP-01 a MFP-08), ver `components/motor_diesel/fmea.json` | ✅ |
| Objetivo intermedio (si hay pocos eventos) | Por ejemplo, fallas de sistemas asociados o hallazgos de inspección | ⬜ |

## 3. Horizonte de predicción

| Campo | Valor | Estado |
|---|---|---|
| Horizonte | 30 días / 250 horas de operación | 🟡 Validar contra tiempos de planificación y de repuestos |
| Justificación | ⬜ Plazo necesario para programar el cambio de motor y disponer del repuesto | ⬜ |

## 4. Baseline (práctica actual)

| Campo | Valor | Estado |
|---|---|---|
| Práctica actual | Reemplazo de motor a las 16.000 h, ajustado por factor de carga (memoria RCM, RCM-002) | ✅ |
| Baseline estadístico | Kaplan-Meier sobre el historial de vida de motores | 🟡 |
| Otros criterios en uso | Límites de laboratorio (SOS) y juicio experto | ⬜ Documentar los límites vigentes |

## 5. Métrica principal y restricciones

| Campo | Valor | Estado |
|---|---|---|
| Métrica principal | ⬜ Por ejemplo: porcentaje de fallas anticipadas con al menos el horizonte de anticipación | ⬜ |
| Restricción de falsas alarmas | ⬜ Por ejemplo: máximo N alertas falsas por equipo-mes | ⬜ |
| Criterio de "supera el baseline" | ⬜ | ⬜ |
| Expectativas acordadas si hay pocos eventos | Reportar intervalos de confianza; considerar el objetivo intermedio | 🟡 |

## 6. Inventario de fuentes y accesos

Detalle técnico en `components/motor_diesel/data_contract.yaml`.

| Fuente | Contenido | Sistema | Responsable de acceso | Estado del acceso |
|---|---|---|---|---|
| Análisis de aceite (SOS) | Fe, Cu, Pb, Na, K, Si, PQI, hollín, viscosidad | ⬜ | ⬜ | ⬜ |
| Inspección de particulado | Filtros, rejillas, patch test | ⬜ | ⬜ | ⬜ |
| VIMS / VisionLink | Presiones, temperaturas, niveles y restricciones | ⬜ | ⬜ | ⬜ |
| Órdenes de trabajo | Eventos de falla y mantenimientos | ⬜ SAP PM / Maximo | ⬜ | ⬜ |
| Horómetro | Horas por equipo y por motor | ⬜ | ⬜ | ⬜ |
| Ciclo de vida de componentes | Instalación y retiro de motores | ⬜ | ⬜ | ⬜ |

## 7. Selección de la flota piloto

Se elige la flota con más eventos y mejor cobertura de datos. Completar con datos reales:

| Indicador | 798AC | 797F |
|---|---|---|
| Camiones en la flota | ⬜ | ⬜ |
| Motores con historial completo (instalación → retiro) | ⬜ | ⬜ |
| Fallas mayores de motor en el historial | ⬜ | ⬜ |
| Motores censurados (retirados sin falla o en operación) | ⬜ | ⬜ |
| Años de historial SOS | ⬜ | ⬜ |
| Años de historial VIMS | ⬜ | ⬜ |
| Conocimiento documentado | Memoria RCM; síntomas por equivalencia (DEC-001) | Síntomas documentados; sin memoria RCM propia |

Opción si ninguna flota tiene eventos suficientes: entrenar con los datos de ambas, usando la equivalencia DEC-001, e informar el desempeño por flota.

## 8. Dataset de eventos etiquetado

| Campo | Estado |
|---|---|
| Listado histórico de eventos construido | ⬜ |
| Validado por Confiabilidad (evento por evento) | ⬜ |
| Componentes censurados identificados | ⬜ |

## 9. Riesgos específicos del caso

| Riesgo | Mitigación |
|---|---|
| Pocos eventos de falla mayor | Modelos de supervivencia, objetivo intermedio y uso conjunto de flotas (DEC-001) |
| Historial de OT mal codificado | Validación evento por evento con Confiabilidad |
| Leakage por fecha de resultado del laboratorio | Regla de corte por `fecha_informe`, no por `fecha_muestra` (contrato de datos) |
| Duty cycle distinto del 798AC (accionamiento eléctrico) | Incluir `modelo_equipo` y variables de carga; reportar desempeño por flota |

## 10. Aprobación (gate Fase 0)

| Rol | Nombre | Fecha | Firma |
|---|---|---|---|
| Confiabilidad | | | |
| Data Analytics | | | |
| Líder de proyecto | | | |

Criterio de salida: ficha firmada, eventos validados por especialista y accesos a las fuentes principales otorgados o con fecha comprometida.
