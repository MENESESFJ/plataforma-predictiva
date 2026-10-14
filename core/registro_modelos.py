"""Registro de experimentos y modelos sobre MLflow (backend SQLite local por defecto).

- Cada entrenamiento aprobado por Validación queda como un run del experimento del
  componente, etiquetado con el request_id que lo originó.
- El modelo se registra con el nombre del componente y el alias "candidato". Pasa a
  "vigente" (el que carga el flujo de inferencia) solo con promover(), después de la
  aprobación humana: el flujo de entrenamiento termina en pendiente_humano.

El tracking URI se toma del argumento, de MLFLOW_TRACKING_URI o, si no hay ninguno, de
sqlite:///mlflow.db en el directorio de trabajo.
"""
import json
import os
from typing import Optional

from contratos.agentes import Contexto, ModeladoSalida

ALIAS_CANDIDATO = "candidato"
ALIAS_VIGENTE = "vigente"


class RegistroModelos:
    def __init__(self, tracking_uri: Optional[str] = None) -> None:
        from mlflow import MlflowClient  # import diferido: MLflow es pesado

        self.uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
        self.cliente = MlflowClient(tracking_uri=self.uri, registry_uri=self.uri)

    def _experimento(self, componente: str) -> str:
        exp = self.cliente.get_experiment_by_name(componente)
        return exp.experiment_id if exp else self.cliente.create_experiment(componente)

    def registrar_entrenamiento(self, ctx: Contexto, modelo: ModeladoSalida) -> str:
        """Registra el run de entrenamiento y devuelve su id de MLflow."""
        run = self.cliente.create_run(self._experimento(ctx.componente),
                                      tags={"request_id": ctx.run_id, "modelo_id": modelo.modelo_id})
        rid = run.info.run_id
        for k, v in {"componente": ctx.componente, "fecha_corte": ctx.fecha_corte.isoformat(),
                     "version_modelo": modelo.version_modelo,
                     "variables": json.dumps(modelo.variables)}.items():
            self.cliente.log_param(rid, k, v)
        for k, v in modelo.metricas.items():
            self.cliente.log_metric(rid, k, v)
        self.cliente.set_terminated(rid)
        return rid

    def registrar_candidato(self, componente: str, run_id: str, modelo: ModeladoSalida) -> str:
        """Crea una versión del modelo del componente y la marca como candidata."""
        if not self.cliente.search_registered_models(f"name = '{componente}'"):
            self.cliente.create_registered_model(componente)
        version = self.cliente.create_model_version(
            componente, source=f"runs:/{run_id}/modelo", run_id=run_id,
            tags={"modelo_id": modelo.modelo_id, "variables": json.dumps(modelo.variables)})
        self.cliente.set_registered_model_alias(componente, ALIAS_CANDIDATO, version.version)
        return str(version.version)

    def promover(self, componente: str, version: str) -> None:
        """Marca una versión como vigente. Solo tras la aprobación humana del entrenamiento."""
        self.cliente.set_registered_model_alias(componente, ALIAS_VIGENTE, str(version))

    def cargar(self, componente: str, alias: str = ALIAS_VIGENTE) -> Optional[ModeladoSalida]:
        """Modelo del componente con ese alias, o None si no hay ninguno."""
        try:
            v = self.cliente.get_model_version_by_alias(componente, alias)
        except Exception:  # sin modelo registrado o sin alias
            return None
        metricas = self.cliente.get_run(v.run_id).data.metrics if v.run_id else {}
        return ModeladoSalida(modelo_id=v.tags.get("modelo_id", componente),
                              version_modelo=str(v.version), metricas=metricas,
                              variables=json.loads(v.tags.get("variables", "[]")))
