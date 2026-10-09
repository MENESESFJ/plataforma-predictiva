"""agentes/interpretacion.py: Razonamiento FMEA multivariable y contextualización SMCS."""
from typing import List, Optional
from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import (
    CompatibilidadSMCS,
    InterpretacionEntrada,
    InterpretacionSalida,
    Severidad,
)
from core.smcs import ConsultorSMCS


class AgenteInterpretacion(BaseAgente):
    nombre = "interpretacion"
    entrada = InterpretacionEntrada
    salida = InterpretacionSalida

    def __init__(self, consultor_smcs: Optional[ConsultorSMCS] = None):
        super().__init__()
        self.consultor_smcs = consultor_smcs or ConsultorSMCS()

    def procesar(self, d: InterpretacionEntrada) -> InterpretacionSalida:
        bundle = cargar_bundle(d.contexto.ruta_componentes, d.contexto.componente)
        modos_fmea = bundle["fmea"]["modos_falla"]

        # 1. Severidad predictiva del modelo
        riesgo_max = max(d.riesgo) if d.riesgo else 0.0
        if riesgo_max >= 0.85:
            nivel_riesgo = Severidad.CRITICA
        elif riesgo_max >= 0.65:
            nivel_riesgo = Severidad.ALTA
        elif riesgo_max >= 0.40:
            nivel_riesgo = Severidad.MEDIA
        else:
            nivel_riesgo = Severidad.BAJA

        # 2. Agregación cuantitativa de SHAP
        pesos = {}
        for s in d.shap:
            for var, contrib in s.items():
                pesos[var] = pesos.get(var, 0.0) + abs(contrib)
        variables_influyentes = sorted(pesos, key=pesos.get, reverse=True)

        # 3. Obtención del sistema (sin cablear MOTOR)
        smcs_cfg = bundle.get("definition", {}).get("smcs_context", {})
        sistema_activo = d.contexto.sistema_smcs or smcs_cfg.get("sistema", "MOTOR")
        codigo_smcs_activo = d.contexto.codigo_smcs  # None si no viene provisto

        # 4. Evaluación de modos FMEA candidatos (recorriendo variables SHAP)
        modos_candidatos: List[dict] = []
        for var in variables_influyentes:
            for modo in modos_fmea:
                if var in modo["variables"] and modo not in modos_candidatos:
                    modos_candidatos.append(modo)

        compatibilidades: List[CompatibilidadSMCS] = []
        modo_seleccionado = None
        severidad_fmea_val = None

        if modos_candidatos and nivel_riesgo in (Severidad.ALTA, Severidad.CRITICA):
            # Tomamos el candidato con mayor cobertura de variables
            modo_seleccionado = modos_candidatos[0]
            try:
                severidad_fmea_val = Severidad(modo_seleccionado.get("severidad", "media").lower())
            except ValueError:
                severidad_fmea_val = None

            # Consultar compatibilidad SMCS para el modo candidato
            compatibilidades = self.consultor_smcs.consultar_compatibilidades(
                id_fmea=modo_seleccionado["id"],
                nombre_fmea=modo_seleccionado["nombre"],
                codigo_smcs=codigo_smcs_activo,
                sistema=sistema_activo,
            )

        # 5. Redacción de narrativa técnica rigurosa (sin declarar causalidad confirmada)
        if modo_seleccionado:
            nombre_mf = modo_seleccionado["nombre"]
            precursores = "; ".join(modo_seleccionado.get("precursores", []))
            diagnostico_partes = [
                f"Alerta predictiva: El equipo presenta nivel de riesgo {nivel_riesgo.value.upper()} "
                f"(probabilidad estimada: {riesgo_max:.2%}). "
                f"La evidencia cuantitativa es compatible con el modo de falla candidato '{nombre_mf}' "
                f"(severidad técnica FMEA: {modo_seleccionado.get('severidad', 'N/A')}). "
                f"Variables de mayor impacto: {', '.join(variables_influyentes[:3])}. "
                f"Precursores analíticos: {precursores}."
            ]

            if compatibilidades:
                comp_principal = compatibilidades[0]
                diagnostico_partes.append(f"Contexto SMCS ({comp_principal.interpretacion}): {comp_principal.observacion}")

            diagnostico = "\n".join(diagnostico_partes)
            id_fmea_final = modo_seleccionado["id"]
            nombre_fmea_final = modo_seleccionado["nombre"]
        else:
            diagnostico = (
                f"Condición operativa estable (Nivel de riesgo: {nivel_riesgo.value}). "
                f"No se detectan precursores críticos de falla activa."
            )
            id_fmea_final = None
            nombre_fmea_final = None

        return InterpretacionSalida(
            riesgo_max=riesgo_max,
            nivel_riesgo=nivel_riesgo,
            severidad_fmea=severidad_fmea_val,
            variables_influyentes=variables_influyentes,
            id_modo_falla=id_fmea_final,
            modo_falla=nombre_fmea_final,
            compatibilidades_smcs=compatibilidades,
            diagnostico=diagnostico,
        )
