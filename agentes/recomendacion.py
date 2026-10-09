"""agentes/recomendacion.py: Vincula diagnóstico con catálogo autorizado de acciones."""
from agentes.base import BaseAgente
from agentes.componentes import cargar_bundle
from contratos.agentes import AccionPropuesta, RecomendacionEntrada, RecomendacionSalida


class AgenteRecomendacion(BaseAgente):
    nombre = "recomendacion"
    entrada = RecomendacionEntrada
    salida = RecomendacionSalida

    def procesar(self, d: RecomendacionEntrada) -> RecomendacionSalida:
        bundle = cargar_bundle(d.contexto.ruta_componentes, d.contexto.componente)
        catalogo = bundle["action_catalog"]["acciones"]

        acciones_sugeridas = []
        for item in catalogo:
            if item["severidad"] == d.severidad.value:
                acciones_sugeridas.append(
                    AccionPropuesta(
                        id=item["id"],
                        accion=item["accion"],
                        urgencia=item["urgencia"],
                        severidad=item["severidad"],
                        estado_revision="pendiente_especialista",
                    )
                )

        if not acciones_sugeridas:
            # Sin fallback: una severidad sin acción autorizada es una brecha del catálogo
            raise ValueError(
                f"catálogo de acciones sin entrada para severidad '{d.severidad.value}'")

        return RecomendacionSalida(acciones=acciones_sugeridas)
