"""Pruebas de los consejos del profesional al paciente (HU-54 / HU-68)."""
import json

import pytest
from django.urls import resolve

from apps.authentication.models import Register
from apps.professionals.models import ConsejoPaciente, PacientesProfesional, PerfilProfesional
from apps.professionals.services import ProfessionalService
from apps.scheduling.models import Notificaciones


def _usuario(email, rol, nombre="Usuario"):
    return Register.objects.create_user(email=email, nombre=nombre, password="Clave123*", rol=rol)


@pytest.fixture
def profesional():
    user = _usuario("pro@test.com", "profesional", "Dra. Ruiz")
    PerfilProfesional.objects.create(idProfesional=user, verificado=True)
    return user


@pytest.fixture
def paciente():
    return _usuario("pac@test.com", "paciente", "Juan")


@pytest.fixture
def asignacion(profesional, paciente):
    return PacientesProfesional.objects.create(idProfesional=profesional, idPaciente=paciente)


@pytest.fixture
def svc():
    return ProfessionalService()


DATOS = {"titulo": "Respiración 4-7-8", "descripcion": "Inhala 4 s, sostén 7 s y exhala 8 s."}


@pytest.mark.django_db
class TestCrearConsejo:
    def test_crea_y_avisa_en_la_campana(self, svc, profesional, paciente, asignacion):
        payload, status = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)

        assert status == 201
        assert payload["consejo"]["titulo"] == "Respiración 4-7-8"
        aviso = Notificaciones.objects.get(idUsuario=paciente, canal="interno", tipo="Consejo")
        assert "Dra. Ruiz" in aviso.mensaje

    def test_profesional_sin_verificar(self, svc, paciente):
        pro = _usuario("nuevo@test.com", "profesional")
        PerfilProfesional.objects.create(idProfesional=pro, verificado=False)

        _, status = svc.crear_consejo(pro.idUsuario, paciente.idUsuario, DATOS)

        assert status == 403

    def test_paciente_no_asignado(self, svc, profesional, paciente):
        payload, status = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)

        assert status == 403
        assert ConsejoPaciente.objects.count() == 0

    def test_titulo_vacio(self, svc, profesional, paciente, asignacion):
        _, status = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, {"titulo": " ", "descripcion": "x"})

        assert status == 400


@pytest.mark.django_db
class TestConsejosDelPaciente:
    def test_lista_con_nombre_del_profesional(self, svc, profesional, paciente, asignacion):
        svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)

        payload, status = svc.consejos_del_paciente(paciente.idUsuario)

        assert status == 200
        assert payload["consejos"][0]["profesional"] == "Dra. Ruiz"

    def test_marcar_completado_y_volver_a_pendiente(self, svc, profesional, paciente, asignacion):
        consejo_id = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)[0]["consejo"]["idConsejo"]

        payload, status = svc.marcar_consejo(paciente.idUsuario, consejo_id, True)
        assert status == 200
        assert payload["consejo"]["completado"] is True
        assert payload["consejo"]["fechaCompletado"] is not None

        payload, _ = svc.marcar_consejo(paciente.idUsuario, consejo_id, False)
        assert payload["consejo"]["completado"] is False
        assert payload["consejo"]["fechaCompletado"] is None

    def test_no_puede_marcar_consejo_de_otro_paciente(self, svc, profesional, paciente, asignacion):
        consejo_id = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)[0]["consejo"]["idConsejo"]
        otro = _usuario("otro@test.com", "paciente")

        _, status = svc.marcar_consejo(otro.idUsuario, consejo_id, True)

        assert status == 404


@pytest.mark.django_db
class TestEliminarConsejo:
    def test_baja_logica_y_desaparece_de_las_listas(self, svc, profesional, paciente, asignacion):
        consejo_id = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)[0]["consejo"]["idConsejo"]

        _, status = svc.eliminar_consejo(profesional.idUsuario, consejo_id)

        assert status == 200
        assert ConsejoPaciente.objects.get(idConsejo=consejo_id).activo is False
        assert svc.consejos_del_paciente(paciente.idUsuario)[0]["consejos"] == []
        assert svc.listar_consejos(profesional.idUsuario, paciente.idUsuario)[0]["consejos"] == []

    def test_no_puede_eliminar_consejo_de_otro_profesional(self, svc, profesional, paciente, asignacion):
        consejo_id = svc.crear_consejo(profesional.idUsuario, paciente.idUsuario, DATOS)[0]["consejo"]["idConsejo"]
        otro = _usuario("otro.pro@test.com", "profesional")

        _, status = svc.eliminar_consejo(otro.idUsuario, consejo_id)

        assert status == 404


def test_rutas_de_consejos():
    assert resolve("/api/profesional/pacientes/5/consejos").url_name == "profesional_paciente_consejos"
    assert resolve("/api/profesional/consejos/3").url_name == "profesional_consejo"
    assert resolve("/api/paciente/consejos").url_name == "paciente_consejos"
    assert resolve("/api/paciente/consejos/3").url_name == "paciente_consejo"


@pytest.mark.django_db
def test_flujo_completo_por_la_api(client, profesional, paciente, asignacion):
    def login(email, rol):
        r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                        content_type="application/json")
        assert r.status_code == 200

    login("pro@test.com", "profesional")
    r = client.post(f"/api/profesional/pacientes/{paciente.idUsuario}/consejos", data=json.dumps(DATOS),
                    content_type="application/json")
    assert r.status_code == 201
    consejo_id = r.json()["consejo"]["idConsejo"]

    login("pac@test.com", "paciente")
    r = client.get("/api/paciente/consejos")
    assert r.status_code == 200
    assert r.json()["consejos"][0]["idConsejo"] == consejo_id

    r = client.patch(f"/api/paciente/consejos/{consejo_id}", data=json.dumps({"completado": True}),
                     content_type="application/json")
    assert r.status_code == 200
    assert r.json()["consejo"]["completado"] is True

    r = client.post(f"/api/profesional/pacientes/{paciente.idUsuario}/consejos", data=json.dumps(DATOS),
                    content_type="application/json")
    assert r.status_code == 403
