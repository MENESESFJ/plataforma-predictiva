"""core/smcs.py: Consultor desacoplado de compatibilidad SMCS."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from contratos.agentes import CompatibilidadSMCS


class ConsultorSMCS:
    # Mapeo discreto de pesos según especificación
    INTERPRETACION_PESO = {
        1.0: "compatible_directo",
        0.7: "compatible_secundario_cercano",
        0.3: "compatible_secundario_amplio",
    }

    def __init__(
        self,
        ruta_csv: str = "knowledge/smcs/Matriz_MF_SMCS_MAESTRO_CONSOLIDADO_v2.csv",
        ruta_homologacion: str = "knowledge/smcs/homologacion_fmea_smcs.json",
    ):
        self.ruta_csv = Path(ruta_csv)
        self.ruta_homologacion = Path(ruta_homologacion)
        # Clave: (sistema, id_mf_smcs, codigo_smcs) -> dict datos
        self._matriz: Dict[Tuple[str, str, str], dict] = {}
        # Múltiples homologaciones por id_fmea
        self._homologaciones: Dict[str, List[dict]] = defaultdict(list)
        self._cargar_recursos()

    def _cargar_recursos(self):
        if self.ruta_homologacion.exists():
            data = json.loads(self.ruta_homologacion.read_text(encoding="utf-8"))
            for m in data.get("mapeos", []):
                self._homologaciones[m["id_fmea"]].append(m)

        if self.ruta_csv.exists():
            with open(self.ruta_csv, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for fila in reader:
                    sist = fila.get("Sistema", "").strip().upper()
                    id_mf = str(fila.get("ID_MF", "")).strip().zfill(4)
                    smcs = str(fila.get("Codigo_SMCS", "")).strip()

                    try:
                        peso_val = float(fila.get("Peso_SMCS", 0.0))
                    except (ValueError, TypeError):
                        peso_val = 0.0

                    clave = (sist, id_mf, smcs)
                    self._matriz[clave] = {
                        "descripcion_mf": fila.get("Descripcion_MF", "").strip(),
                        "descripcion_smcs": fila.get("Descripcion_SMCS", "").strip(),
                        "peso": peso_val,
                        "tipo": fila.get("Tipo", "").strip(),
                    }

    def consultar_compatibilidades(
        self,
        id_fmea: Optional[str],
        nombre_fmea: Optional[str],
        codigo_smcs: Optional[str],
        sistema: Optional[str],
    ) -> List[CompatibilidadSMCS]:
        """Evalúa todas las homologaciones candidatas sin supuestos ni datos inventados."""
        # Caso 1: Código SMCS o Sistema no suministrado -> no_evaluado
        if not codigo_smcs or not sistema:
            return [
                CompatibilidadSMCS(
                    sistema=sistema or "NO_ESPECIFICADO",
                    id_fmea=id_fmea or "N/A",
                    nombre_fmea=nombre_fmea,
                    codigo_smcs=codigo_smcs,
                    tipo_asociacion_smcs=None,
                    peso_referencia=None,
                    interpretacion="no_evaluado",
                    estado_homologacion="datos_insuficientes",
                    observacion="Código SMCS o Sistema no entregado en el contexto; evaluación omitida.",
                )
            ]

        homologaciones = self._homologaciones.get(id_fmea, [])
        if not homologaciones:
            return [
                CompatibilidadSMCS(
                    sistema=sistema,
                    id_fmea=id_fmea or "N/A",
                    nombre_fmea=nombre_fmea,
                    codigo_smcs=codigo_smcs,
                    tipo_asociacion_smcs="No identificado",
                    peso_referencia=None,
                    interpretacion="relacion_no_identificada",
                    estado_homologacion="no_homologado",
                    observacion=f"El modo FMEA '{id_fmea}' no posee homologación registrada en la tabla.",
                )
            ]

        resultados: List[CompatibilidadSMCS] = []
        codigo_smcs_limpio = str(codigo_smcs).strip()
        sistema_limpio = sistema.strip().upper()

        for hom in homologaciones:
            id_mf_smcs = str(hom["id_mf_smcs"]).strip().zfill(4)
            clave = (sistema_limpio, id_mf_smcs, codigo_smcs_limpio)
            relacion_hom = hom.get("relacion", "parcial")
            estado_rev = hom.get("estado_revision", "pendiente_revision")

            if clave in self._matriz:
                registro = self._matriz[clave]
                peso = registro["peso"]
                tipo = registro["tipo"]

                # Validación de consistencia Tipo vs Peso
                es_consistente = (
                    (tipo.lower() == "directo" and peso == 1.0)
                    or (tipo.lower() == "secundario" and peso in (0.7, 0.3))
                )

                if not es_consistente:
                    interp = "inconsistente_tipo_peso"
                    obs = (
                        f"Inconsistencia en matriz SMCS: Tipo '{tipo}' no concuerda con peso {peso}. "
                        f"Requiere auditoría de datos."
                    )
                else:
                    interp = self.INTERPRETACION_PESO.get(peso, "peso_no_reconocido")
                    if peso == 1.0:
                        obs = (
                            f"El modo de falla presenta una asociación directa con el código SMCS {codigo_smcs_limpio} "
                            f"({registro['descripcion_smcs']}). Esta relación respalda su compatibilidad con el componente, "
                            f"pero no confirma por sí sola la causa raíz."
                        )
                    elif peso == 0.7:
                        obs = (
                            f"El modo de falla presenta una asociación secundaria cercana con el código SMCS {codigo_smcs_limpio}. "
                            f"Debe contrastarse con las variables de condición y precursores."
                        )
                    else:
                        obs = (
                            f"El modo de falla presenta una asociación secundaria amplia con el código SMCS {codigo_smcs_limpio}. "
                            f"Evidencia contextual de menor cercanía."
                        )

                resultados.append(
                    CompatibilidadSMCS(
                        sistema=sistema_limpio,
                        id_fmea=id_fmea,
                        nombre_fmea=nombre_fmea,
                        id_mf_smcs=id_mf_smcs,
                        descripcion_mf_smcs=registro["descripcion_mf"],
                        relacion_homologacion=relacion_hom,
                        estado_homologacion=estado_rev,
                        codigo_smcs=codigo_smcs_limpio,
                        descripcion_smcs=registro["descripcion_smcs"],
                        tipo_asociacion_smcs=tipo,
                        peso_referencia=peso,
                        interpretacion=interp,
                        observacion=obs,
                    )
                )
            else:
                # Homologación existe pero el SMCS no está asociado a ese modo en la matriz
                resultados.append(
                    CompatibilidadSMCS(
                        sistema=sistema_limpio,
                        id_fmea=id_fmea,
                        nombre_fmea=nombre_fmea,
                        id_mf_smcs=id_mf_smcs,
                        descripcion_mf_smcs=hom.get("descripcion_mf_smcs"),
                        relacion_homologacion=relacion_hom,
                        estado_homologacion=estado_rev,
                        codigo_smcs=codigo_smcs_limpio,
                        tipo_asociacion_smcs="No identificado",
                        peso_referencia=None,
                        interpretacion="relacion_no_identificada",
                        observacion=(
                            f"No se encontró relación registrada entre el modo {id_fmea} (SMCS {id_mf_smcs}) "
                            f"y el código SMCS {codigo_smcs_limpio}. Esto no descarta el modo de falla, pero "
                            f"reduce el respaldo contextual disponible y requiere revisión técnica."
                        ),
                    )
                )

        # Ordenar priorizando compatibilidad directa (1.0), luego secundaria (0.7, 0.3)
        resultados.sort(key=lambda x: (x.peso_referencia or 0.0), reverse=True)
        return resultados
