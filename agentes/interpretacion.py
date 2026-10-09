"""agentes/interpretacion.py: Traduce SHAP y riesgo en diagnóstico con FMEA."""
from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import InterpretacionEntrada, InterpretacionSalida, Severidad


class AgenteInterpretacion(BaseAgente):
    nombre = "interpretacion"
    entrada = InterpretacionEntrada
    salida = InterpretacionSalida

    def procesar(self, d: InterpretacionEntrada) -> InterpretacionSalida:
        bundle = cargar_bundle(d.contexto.ruta_componentes, d.contexto.componente)
        modos_fmea = bundle["fmea"]["modos_falla"]

        riesgo_max = max(d.riesgo) if d.riesgo else 0.0

        if riesgo_max >= 0.85:
            sev = Severidad.CRITICA
        elif riesgo_max >= 0.65:
            sev = Severidad.ALTA
        elif riesgo_max >= 0.40:
            sev = Severidad.MEDIA
        else:
            sev = Severidad.BAJA

        # Agregación de impacto SHAP global
        pesos = {}
        for s in d.shap:
            for var, contrib in s.items():
                pesos[var] = pesos.get(var, 0.0) + abs(contrib)

        variables_influyentes = sorted(pesos, key=pesos.get, reverse=True)
        modo_detectado = None
        diagnostico = "Condición operativa dentro de parámetros estándar."

        if variables_influyentes and sev in (Severidad.ALTA, Severidad.CRITICA):
            var_principal = variables_influyentes[0]
            for modo in modos_fmea:
                if var_principal in modo["variables"]:
                    modo_detectado = modo["nombre"]
                    precursores = "; ".join(modo.get("precursores", []))
                    diagnostico = (
                        f"Alerta preventiva: se detecta probable '{modo['nombre']}' "
                        f"(Severidad: {modo['severidad']}) evidenciado por alteración en '{var_principal}'. "
                        f"Precursores: {precursores}."
                    )
                    break

        return InterpretacionSalida(
            riesgo_max=riesgo_max,
            severidad=sev,
            variables_influyentes=variables_influyentes,
            modo_falla=modo_detectado,
            diagnostico=diagnostico,
        )
