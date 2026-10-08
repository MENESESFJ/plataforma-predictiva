# Agente 1: Supervisor (Orquestador Determinístico)

## Propósito
Coordinar la ejecución integral de los flujos de la plataforma (Entrenamiento o Inferencia) actuando como una máquina de estados finita y determinística. Garantiza la persistencia del Estado y el cumplimiento estricto de los contratos y gates de salida.

## Tipo de Componente
- **Naturaleza:** 100% Determinístico (Código Python / Máquina de Estados).
- **Uso de LLM:** Ninguno en Etapa 1.

## Responsabilidades
1. Recibir la solicitud (`request_id`, `caso_uso_id`, `equipo`, `tipo_flujo`, `fecha_corte`).
2. Cargar el `ComponentBundle` correspondiente al componente del caso de uso.
3. Despachar secuencialmente a los agentes según el flujo:
   - **Inferencia:** Datos → Calidad → Features → Servicio Inferencia → Interpretación → Recomendación → Human-in-the-Loop.
   - **Entrenamiento:** Datos → Calidad → Features → Modelamiento → Validación → Human-in-the-Loop.
4. Persistir el objeto `Estado` tras cada transición y registrar trazas de auditoría.
5. Detener el flujo de inmediato ante caídas de calidad, errores de esquema o excepciones no controladas.

## Contratos
- **Entrada:** `contratos.supervisor.SupervisorInput`
- **Salida:** `contratos.base.Estado`
