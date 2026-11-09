"""Pruebas de "Descargar mis datos" (HU-66, Ley 1581 de 2012)."""
import json
from datetime import date, time

import pytest

from apps.authentication.models import Register
from apps.patients.repositories import PatientRepository
from apps.professionals.models import ConsejoPaciente, PacientesProfesional, PerfilProfesional
from apps.scheduling.models import CalificacionCita, Citas


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


@pytest.mark.django_db
class TestExportarDatos:
    def test_incluye_consejos_activos_con_su_profesional(self, paciente, profesional):
        asignacion = PacientesProfesional.objects.create(idProfesional=profesional, idPaciente=paciente)
        ConsejoPaciente.objects.create(idAsignacion=asignacion, titulo="Caminar", descripcion="20 minutos")
        ConsejoPaciente.objects.create(idAsignacion=asignacion, titulo="Borrado", descripcion="x", activo=False)

        data = PatientRepository().exportar_datos_usuario(paciente.idUsuario)

        assert [c["titulo"] for c in data["consejos"]] == ["Caminar"]
        assert data["consejos"][0]["idAsignacion__idProfesional__nombre"] == "Dra. Ruiz"

    def test_citas_traen_la_calificacion(self, paciente, profesional):
        cita = Citas.objects.create(
            idPaciente=paciente, idProfesional=profesional, fecha=date(2026, 11, 3), hora=time(9, 0),
            tipoCita="Virtual", motivo="Control", estado="Completada",
        )
        CalificacionCita.objects.create(idCita=cita, puntuacion=4, comentario="Bien")

        data = PatientRepository().exportar_datos_usuario(paciente.idUsuario)

        assert data["citas"][0]["calificacion__puntuacion"] == 4
        assert data["citas"][0]["calificacion__comentario"] == "Bien"

    def test_no_trae_consejos_de_otros_pacientes(self, paciente, profesional):
        otro = _usuario("otro@test.com", "paciente")
        asignacion = PacientesProfesional.objects.create(idProfesional=profesional, idPaciente=otro)
        ConsejoPaciente.objects.create(idAsignacion=asignacion, titulo="Ajeno", descripcion="x")

        data = PatientRepository().exportar_datos_usuario(paciente.idUsuario)

        assert data["consejos"] == []


@pytest.mark.django_db
def test_pagina_y_api_solo_para_el_paciente(client, paciente, profesional):
    def login(email, rol):
        r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                        content_type="application/json")
        assert r.status_code == 200

    login("pac@test.com", "paciente")
    assert client.get("/aside-patient/mis-datos.html").status_code == 200
    r = client.get("/api/paciente/mis-datos")
    assert r.status_code == 200
    assert "consejos" in r.json()["data"]

    login("pro@test.com", "profesional")
    assert client.get("/api/paciente/mis-datos").status_code == 403
