"""agentes/calidad.py: Auditoría técnica y compuerta de contención determinística."""
from typing import List, Dict, Any
from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import CalidadEntrada, CalidadSalida, VeredictoCalidad


class AgenteCalidad(BaseAgente):
    nombre = "calidad"
    entrada = CalidadEntrada
    salida = CalidadSalida

    def procesar(self, d: CalidadEntrada) -> CalidadSalida:
        bundle = cargar_bundle(d.contexto.ruta_componentes, d.contexto.componente)
        config_calidad = bundle["quality_rules"]
        reglas = config_calidad["reglas"]
        umbral_aprobado = config_calidad.get("umbral_score_aprobado", 90)

        registros_validos: List[Dict[str, Any]] = []
        violaciones: List[str] = []
        puntos_penalizacion = 0.0

        total_reg = len(d.registros)
        if total_reg == 0:
            return CalidadSalida(
                veredicto=VeredictoCalidad.RECHAZADO,
                score_calidad=0.0,
                registros_validos=[],
                n_rechazados=0,
                violaciones=["Snapshot vacío: 0 registros"],
            )

        for i, reg in enumerate(d.registros):
            errores_registro = []
            for regla in reglas:
                var = regla["variable"]
                val = reg.get(var)

                if val is None or not isinstance(val, (int, float)):
                    errores_registro.append(f"{var} ausente/no numérico")
                elif not (regla["min"] <= val <= regla["max"]):
                    errores_registro.append(f"{var}={val} fuera de rango [{regla['min']}, {regla['max']}]")

            if errores_registro:
                violaciones.append(f"Reg {i}: " + "; ".join(errores_registro))
                puntos_penalizacion += 1.0
            else:
                registros_validos.append(reg)

        tasa_fallas = puntos_penalizacion / total_reg
        score = round(max(0.0, (1.0 - tasa_fallas) * 100.0), 2)

        if score >= umbral_aprobado:
            veredicto = VeredictoCalidad.APROBADO
        elif score >= (umbral_aprobado * 0.75):
            veredicto = VeredictoCalidad.APROBADO_CON_OBSERVACIONES
        else:
            veredicto = VeredictoCalidad.RECHAZADO

        return CalidadSalida(
            veredicto=veredicto,
            score_calidad=score,
            registros_validos=registros_validos,
            n_rechazados=int(puntos_penalizacion),
            violaciones=violaciones,
        )
