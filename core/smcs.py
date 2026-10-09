"""core/smcs.py: Consultor desacoplado de compatibilidad SMCS."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from contratos.agentes import CompatibilidadSMCS


class ConsultorSMCS:
    INTERPRETACION_PESO = {
        1.0: "compatible_directo",
        0.7: "compatible_secundario_cercano",
        0.3: "compatible_secundario_amplio",
    }

    def __init__(
        self,
        ruta_csv: str = "knowledge/smcs/Matriz_MF_SMCS_MAESTRO_CONSOLIDADO_v2.csv",
        ruta_homologacion: str = "knowledge/smcs/homologacion_fmea_smcs.json",
        permitir_solo_aprobados: bool = True,
    ):
        self.ruta_csv = Path(ruta_csv)
        self.ruta_homologacion = Path(ruta_homologacion)
        self.permitir_solo_aprobados = permitir_solo_aprobados
        
        self._matriz: Dict[Tuple[str, str, str], dict] = {}
        # Mapeos activos para runtime
        self._homologaciones_activas: Dict[str, List[dict]] = defaultdict(list)
        # Todos los mapeos (incluye propuestos y pendientes) para auditoría técnica
        self._homologaciones_todas: Dict[str, List[dict]] = defaultdict(list)
        self._pendientes_revision: Dict[str, dict] = {}

        self._cargar_recursos()

    def _cargar_recursos(self):
        if self.ruta_homologacion.exists():
            data = json.loads(self.ruta_homologacion.read_text(encoding="utf-8"))
            
            for m in data.get("mapeos", []):
                self._homologaciones_todas[m["id_fmea"]].append(m)
                # Regla de seguridad runtime: solo activo=True y aprobado
                if m.get("activo") is True and m.get("estado_revision") == "aprobado":
                    self._homologaciones_activas[m["id_fmea"]].append(m)

            for p in data.get("pendientes_revision", []):
                self._pendientes_revision[p["id_fmea"]] = p

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
        """Evalúa compatibilidad según matriz y homologaciones controladas."""
        sistema_limpio = (sistema or "NO_ESPECIFICADO").strip().upper()

        # 1. Validación de entradas mínimas
        if not codigo_smcs or not sistema:
            return [
                CompatibilidadSMCS(
                    sistema=sistema_limpio,
                    id_fmea=id_fmea or "N/A",
                    nombre_fmea=nombre_fmea,
                    codigo_smcs=codigo_smcs,
                    interpretacion="no_evaluado",
                    estado_homologacion="datos_insuficientes",
                    activo_en_runtime=False,
                    observacion="Código SMCS o Sistema no suministrado; contextualización omitida.",
                )
            ]

        codigo_smcs_limpio = str(codigo_smcs).strip()

        # 2. Selección de homologaciones según modo runtime
        homologaciones = (
            self._homologaciones_activas.get(id_fmea, [])
            if self.permitir_solo_aprobados
            else self._homologaciones_todas.get(id_fmea, [])
        )

        # 3. Si no hay homologación activa pero está en pendientes_revision o en propuestas inactivas
        if not homologaciones:
            # ¿Existe como propuesta inactiva?
            propuestas = self._homologaciones_todas.get(id_fmea, [])
            if propuestas and self.permitir_solo_aprobados:
                return [
                    CompatibilidadSMCS(
                        sistema=sistema_limpio,
                        id_fmea=id_fmea or "N/A",
                        nombre_fmea=nombre_fmea,
                        codigo_smcs=codigo_smcs_limpio,
                        interpretacion="homologacion_no_aprobada",
                        estado_homologacion=propuestas[0].get("estado_revision", "propuesto"),
                        activo_en_runtime=False,
                        observacion=(
                            f"El modo FMEA '{id_fmea}' cuenta con homologación registrada pero "
                            f"está en estado '{propuestas[0].get('estado_revision')}' (activo=False). "
                            f"No se utiliza como respaldo en runtime hasta su aprobación técnica."
                        ),
                    )
                ]

            # ¿Existe documentado en pendientes_revision?
            pendiente = self._pendientes_revision.get(id_fmea)
            if pendiente:
                return [
                    CompatibilidadSMCS(
                        sistema=sistema_limpio,
                        id_fmea=id_fmea or "N/A",
                        nombre_fmea=nombre_fmea,
                        codigo_smcs=codigo_smcs_limpio,
                        interpretacion="sin_equivalencia",
                        estado_homologacion=pendiente.get("estado_revision", "pendiente_revision"),
                        activo_en_runtime=False,
                        observacion=(
                            f"Modo FMEA '{id_fmea}' documentado sin equivalencia directa en SMCS. "
                            f"Motivo: {pendiente.get('motivo')}"
                        ),
                    )
                ]

            # Sin registro alguno
            return [
                CompatibilidadSMCS(
                    sistema=sistema_limpio,
                    id_fmea=id_fmea or "N/A",
                    nombre_fmea=nombre_fmea,
                    codigo_smcs=codigo_smcs_limpio,
                    interpretacion="relacion_no_identificada",
                    estado_homologacion="no_homologado",
                    activo_en_runtime=False,
                    observacion=f"El modo FMEA '{id_fmea}' no posee homologación registrada en la base de conocimiento.",
                )
            ]

        # 4. Evaluación de las homologaciones habilitadas contra la matriz CSV
        resultados: List[CompatibilidadSMCS] = []

        for hom in homologaciones:
            id_mf_smcs = str(hom["id_mf_smcs"]).strip().zfill(4)
            clave = (sistema_limpio, id_mf_smcs, codigo_smcs_limpio)

            cardinalidad = hom.get("cardinalidad")
            tipo_eq = hom.get("tipo_equivalencia")
            dir_esp = hom.get("direccion_especificidad")
            estado_rev = hom.get("estado_revision", "propuesto")
            activo = hom.get("activo", False)

            if clave in self._matriz:
                registro = self._matriz[clave]
                peso = registro["peso"]
                tipo = registro["tipo"]

                # Consistencia entre Tipo y Peso
                es_consistente = (
                    (tipo.lower() == "directo" and peso == 1.0)
                    or (tipo.lower() == "secundario" and peso in (0.7, 0.3))
                )

                if not es_consistente:
                    interp = "inconsistente_tipo_peso"
                    obs = f"Inconsistencia en matriz SMCS: Tipo '{tipo}' no coincide con Peso {peso}."
                else:
                    interp = self.INTERPRETACION_PESO.get(peso, "peso_no_reconocido")
                    if peso == 1.0:
                        obs = (
                            f"El modo de falla presenta asociación directa con el código SMCS {codigo_smcs_limpio} "
                            f"({registro['descripcion_smcs']}). Respalda compatibilidad, pero no confirma causa raíz."
                        )
                    elif peso == 0.7:
                        obs = (
                            f"El modo de falla presenta asociación secundaria cercana (peso 0.7) con el código SMCS {codigo_smcs_limpio}."
                        )
                    else:
                        obs = (
                            f"El modo de falla presenta asociación secundaria amplia (peso 0.3) con el código SMCS {codigo_smcs_limpio}."
                        )

                resultados.append(
                    CompatibilidadSMCS(
                        sistema=sistema_limpio,
                        id_fmea=id_fmea,
                        nombre_fmea=nombre_fmea,
                        id_mf_smcs=id_mf_smcs,
                        descripcion_mf_smcs=registro["descripcion_mf"],
                        cardinalidad=cardinalidad,
                        tipo_equivalencia=tipo_eq,
                        direccion_especificidad=dir_esp,
                        estado_homologacion=estado_rev,
                        activo_en_runtime=activo,
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
                        cardinalidad=cardinalidad,
                        tipo_equivalencia=tipo_eq,
                        direccion_especificidad=dir_esp,
                        estado_homologacion=estado_rev,
                        activo_en_runtime=activo,
                        codigo_smcs=codigo_smcs_limpio,
                        tipo_asociacion_smcs="No identificado",
                        peso_referencia=None,
                        interpretacion="relacion_no_identificada",
                        observacion=(
                            f"No se encontró relación registrada entre el modo {id_fmea} (SMCS {id_mf_smcs}) "
                            f"y el código SMCS {codigo_smcs_limpio}. No descarta el modo, pero carece de respaldo contextual."
                        ),
                    )
                )

        resultados.sort(key=lambda x: (x.peso_referencia or 0.0), reverse=True)
        return resultados
