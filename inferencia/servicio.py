"""inferencia/servicio.py: Motor de cómputo determinístico de riesgo y SHAP."""
import math
from typing import Dict, List, Tuple
from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import InferenciaEntrada, InferenciaSalida


class ServicioInferencia(BaseAgente):
    nombre = "inferencia"
    entrada = InferenciaEntrada
    salida = InferenciaSalida

    def _obtener_rangos_normalizacion(self, ctx) -> Dict[str, Tuple[float, float]]:
        bundle = cargar_bundle(ctx.ruta_componentes, ctx.componente)
        return {
            r["variable"]: (float(r["min"]), float(r["max"]))
            for r in bundle["quality_rules"]["reglas"]
        }

    def procesar(self, d: InferenciaEntrada) -> InferenciaSalida:
        rangos = self._obtener_rangos_normalizacion(d.contexto)
        esperadas = set(d.variables_modelo)
        
        riesgos: List[float] = []
        shaps: List[Dict[str, float]] = []

        for idx, feat in enumerate(d.features):
            presentes = set(feat.keys())
            if not esperadas.issubset(presentes):
                faltantes = esperadas - presentes
                raise ValueError(f"Fila {idx}: faltan variables esperadas por el modelo: {faltantes}")

            contribuciones: Dict[str, float] = {}
            score_lineal = 0.0

            for var in d.variables_modelo:
                val = float(feat[var])
                lo, hi = rangos.get(var, (0.0, 100.0))
                
                # Normalización centrada [-0.5, 0.5]
                rango = hi - lo if hi != lo else 1.0
                norm_val = (val - lo) / rango - 0.5
                
                # Ponderación según impacto físico conocido
                peso = 1.5 if var in ("pqi", "cu_ppm", "presion_carter") else 1.0
                shap_val = round(norm_val * peso, 4)
                
                contribuciones[var] = shap_val
                score_lineal += shap_val

            # Función logística para riesgo acumulado en [0.0, 1.0]
            prob_falla = round(1.0 / (1.0 + math.exp(-3.5 * score_lineal)), 4)
            riesgos.append(prob_falla)
            shaps.append(contribuciones)

        return InferenciaSalida(riesgo=riesgos, shap=shaps)
