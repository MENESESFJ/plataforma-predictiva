# tests/test_smcs_servicio.py
import pytest
from core.smcs import ConsultorSMCS


@pytest.fixture
def consultor_con_datos(tmp_path):
    # CSV controlado
    csv_file = tmp_path / "matriz_test.csv"
    csv_file.write_text(
        "Sistema,ID_MF,Descripcion_MF,Codigo_SMCS,Descripcion_SMCS,Peso_SMCS,Tipo\n"
        "MOTOR,0058,Temperatura Alta,1020,Block largo,1.0,Directo\n"
        "MOTOR,0058,Temperatura Alta,1052,Turboalimentador,0.7,Secundario\n"
        "MOTOR,0062,Presión Baja,1101,Cabezal,0.3,Secundario\n"
        "MOTOR,0014,Lubricación Deficiente,1020,Block,0.3,Directo\n",  # Inconsistencia intencional
        encoding="utf-8"
    )

    # Homologación con múltiples mapeos aprobados y activos (únicos usados en runtime)
    json_file = tmp_path / "homologacion_test.json"
    json_file.write_text(
        """{
          "version": "1.0.0",
          "mapeos": [
            {
              "id_fmea": "MF-001",
              "id_mf_smcs": "0058",
              "descripcion_mf_smcs": "Temperatura Alta",
              "cardinalidad": "uno_a_uno",
              "tipo_equivalencia": "parcial",
              "direccion_especificidad": "fmea_mas_especifico",
              "estado_revision": "aprobado",
              "activo": true
            },
            {
              "id_fmea": "MF-002",
              "id_mf_smcs": "0014",
              "descripcion_mf_smcs": "Lubricación Deficiente",
              "cardinalidad": "uno_a_uno",
              "tipo_equivalencia": "parcial",
              "direccion_especificidad": "fmea_mas_especifico",
              "estado_revision": "aprobado",
              "activo": true
            }
          ]
        }""",
        encoding="utf-8"
    )

    return ConsultorSMCS(ruta_csv=str(csv_file), ruta_homologacion=str(json_file))


def test_smcs_asociacion_directa_exacta(consultor_con_datos):
    res = consultor_con_datos.consultar_compatibilidades(
        id_fmea="MF-001", nombre_fmea="sobrecalentamiento", codigo_smcs="1020", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "compatible_directo"
    assert res[0].tipo_asociacion_smcs == "Directo"
    assert res[0].peso_referencia == 1.0
    assert res[0].id_mf_smcs == "0058"
    assert res[0].tipo_equivalencia == "parcial"
    assert res[0].estado_homologacion == "aprobado"
    assert res[0].activo_en_runtime is True


def test_smcs_asociacion_secundaria_cercana(consultor_con_datos):
    res = consultor_con_datos.consultar_compatibilidades(
        id_fmea="MF-001", nombre_fmea="sobrecalentamiento", codigo_smcs="1052", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "compatible_secundario_cercano"
    assert res[0].peso_referencia == 0.7


def test_smcs_no_evaluado_cuando_falta_codigo(consultor_con_datos):
    # No se debe inventar 1020
    res = consultor_con_datos.consultar_compatibilidades(
        id_fmea="MF-001", nombre_fmea="sobrecalentamiento", codigo_smcs=None, sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "no_evaluado"
    assert res[0].codigo_smcs is None


def test_smcs_relacion_no_identificada_no_descarta(consultor_con_datos):
    res = consultor_con_datos.consultar_compatibilidades(
        id_fmea="MF-001", nombre_fmea="sobrecalentamiento", codigo_smcs="9999", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "relacion_no_identificada"
    assert "No descarta el modo" in res[0].observacion


def test_smcs_inconsistencia_tipo_peso(consultor_con_datos):
    # En fixture: Tipo Directo pero peso 0.3
    res = consultor_con_datos.consultar_compatibilidades(
        id_fmea="MF-002", nombre_fmea="desgaste_cojinetes", codigo_smcs="1020", sistema="MOTOR"
    )
    assert len(res) == 1
    assert res[0].interpretacion == "inconsistente_tipo_peso"
