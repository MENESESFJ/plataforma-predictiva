# tests/test_smcs_ontologia.py
import pytest
from core.smcs import ConsultorSMCS


@pytest.fixture
def fixtures_ontologia(tmp_path):
    csv_file = tmp_path / "matriz_maestro.csv"
    csv_file.write_text(
        "Sistema,ID_MF,Descripcion_MF,Codigo_SMCS,Descripcion_SMCS,Peso_SMCS,Tipo\n"
        "MOTOR,0058,Temperatura Alta,1020,Block largo,1.0,Directo\n"
        "MOTOR,0062,Presión Baja,1101,Cabezal,0.3,Secundario\n",
        encoding="utf-8"
    )

    json_file = tmp_path / "homologacion.json"
    json_file.write_text(
        """{
          "version": "1.1.0",
          "mapeos": [
            {
              "id_fmea": "MF-001",
              "nombre_fmea": "sobrecalentamiento",
              "sistema": "MOTOR",
              "id_mf_smcs": "0058",
              "descripcion_mf_smcs": "Temperatura Alta",
              "cardinalidad": "uno_a_uno",
              "tipo_equivalencia": "parcial",
              "direccion_especificidad": "fmea_mas_especifico",
              "estado_revision": "propuesto",
              "activo": false
            },
            {
              "id_fmea": "MF-005_APROBADO",
              "nombre_fmea": "test_aprobado",
              "sistema": "MOTOR",
              "id_mf_smcs": "0058",
              "descripcion_mf_smcs": "Temperatura Alta",
              "cardinalidad": "uno_a_uno",
              "tipo_equivalencia": "parcial",
              "direccion_especificidad": "fmea_mas_especifico",
              "estado_revision": "aprobado",
              "activo": true
            }
          ],
          "pendientes_revision": [
            {
              "id_fmea": "MF-002",
              "nombre_fmea": "desgaste_cojinetes",
              "sistema": "MOTOR",
              "motivo": "No existe un modo genérico denominado Desgaste en la matriz SMCS.",
              "estado_revision": "pendiente_revision"
            }
          ]
        }""",
        encoding="utf-8"
    )
    return str(csv_file), str(json_file)


def test_bloqueo_runtime_para_propuesta_inactiva(fixtures_ontologia):
    ruta_csv, ruta_json = fixtures_ontologia
    consultor = ConsultorSMCS(ruta_csv=ruta_csv, ruta_homologacion=ruta_json, permitir_solo_aprobados=True)
    
    # MF-001 es 'propuesto' y activo=False
    res = consultor.consultar_compatibilidades(
        id_fmea="MF-001", nombre_fmea="sobrecalentamiento", codigo_smcs="1020", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "homologacion_no_aprobada"
    assert res[0].activo_en_runtime is False
    assert "No se utiliza como respaldo en runtime" in res[0].observacion


def test_tratamiento_modo_en_pendientes_revision(fixtures_ontologia):
    ruta_csv, ruta_json = fixtures_ontologia
    consultor = ConsultorSMCS(ruta_csv=ruta_csv, ruta_homologacion=ruta_json, permitir_solo_aprobados=True)

    # MF-002 está documentado en pendientes_revision
    res = consultor.consultar_compatibilidades(
        id_fmea="MF-002", nombre_fmea="desgaste_cojinetes", codigo_smcs="1020", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "sin_equivalencia"
    assert "No existe un modo genérico denominado Desgaste" in res[0].observacion


def test_aprobado_y_activo_se_evalua_correctamente(fixtures_ontologia):
    ruta_csv, ruta_json = fixtures_ontologia
    consultor = ConsultorSMCS(ruta_csv=ruta_csv, ruta_homologacion=ruta_json, permitir_solo_aprobados=True)

    # MF-005_APROBADO es activo=True y aprobado
    res = consultor.consultar_compatibilidades(
        id_fmea="MF-005_APROBADO", nombre_fmea="test_aprobado", codigo_smcs="1020", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "compatible_directo"
    assert res[0].tipo_asociacion_smcs == "Directo"
    assert res[0].peso_referencia == 1.0
    assert res[0].activo_en_runtime is True
    assert res[0].cardinalidad == "uno_a_uno"
    assert res[0].tipo_equivalencia == "parcial"
