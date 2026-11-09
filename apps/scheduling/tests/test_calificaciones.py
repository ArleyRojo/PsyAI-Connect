"""Pruebas de la calificación de citas completadas (HU-67)."""
import json
from datetime import date, time

import pytest

from apps.authentication.models import Register
from apps.patients.repositories import PatientRepository
from apps.professionals.models import PerfilProfesional
from apps.scheduling.models import CalificacionCita, Citas
from apps.scheduling.services import AppointmentService


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


def _cita(paciente, profesional, estado="Completada", hora=time(9, 0)):
    return Citas.objects.create(
        idPaciente=paciente, idProfesional=profesional, fecha=date(2026, 11, 3), hora=hora,
        tipoCita="Virtual", motivo="Control", estado=estado,
    )


@pytest.fixture
def svc():
    return AppointmentService()


@pytest.mark.django_db
class TestCalificarCita:
    def test_califica_cita_completada(self, svc, paciente, profesional):
        cita = _cita(paciente, profesional)

        payload, status = svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": 5, "comentario": "Muy amable"})

        assert status == 200
        assert payload["calificacion"]["puntuacion"] == 5
        assert CalificacionCita.objects.get(idCita=cita).comentario == "Muy amable"

    def test_puede_editar_su_calificacion(self, svc, paciente, profesional):
        cita = _cita(paciente, profesional)
        svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": 2})

        payload, status = svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": 4})

        assert status == 200
        assert payload["message"] == "Calificación actualizada"
        assert CalificacionCita.objects.count() == 1
        assert CalificacionCita.objects.get().puntuacion == 4

    @pytest.mark.parametrize("estado", ["Pendiente", "Confirmada", "Cancelada"])
    def test_solo_citas_completadas(self, svc, paciente, profesional, estado):
        cita = _cita(paciente, profesional, estado=estado)

        _, status = svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": 5})

        assert status == 400
        assert CalificacionCita.objects.count() == 0

    @pytest.mark.parametrize("puntuacion", [0, 6, "abc", None])
    def test_puntuacion_invalida(self, svc, paciente, profesional, puntuacion):
        cita = _cita(paciente, profesional)

        _, status = svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": puntuacion})

        assert status == 400

    def test_comentario_muy_largo(self, svc, paciente, profesional):
        cita = _cita(paciente, profesional)

        _, status = svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": 5, "comentario": "x" * 501})

        assert status == 400

    def test_no_puede_calificar_cita_de_otro_paciente(self, svc, paciente, profesional):
        cita = _cita(paciente, profesional)
        otro = _usuario("otro@test.com", "paciente")

        _, status = svc.calificar_cita(otro.idUsuario, cita.idCita, {"puntuacion": 5})

        assert status == 404


@pytest.mark.django_db
class TestResumenDeCalificaciones:
    def test_profesional_ve_promedio_y_comentarios_anonimos(self, svc, paciente, profesional):
        svc.calificar_cita(paciente.idUsuario, _cita(paciente, profesional).idCita, {"puntuacion": 5, "comentario": "Excelente"})
        svc.calificar_cita(paciente.idUsuario, _cita(paciente, profesional, hora=time(10, 0)).idCita, {"puntuacion": 4})

        payload, status = svc.mis_calificaciones(profesional.idUsuario)

        assert status == 200
        assert payload["promedio"] == 4.5
        assert payload["total"] == 2
        assert set(payload["calificaciones"][0]) == {"puntuacion", "comentario", "fecha"}

    def test_lista_publica_de_profesionales_trae_promedio(self, svc, paciente, profesional):
        svc.calificar_cita(paciente.idUsuario, _cita(paciente, profesional).idCita, {"puntuacion": 3})

        profesionales = PatientRepository().list_professionals()

        assert profesionales[0]["promedioCalificacion"] == 3.0
        assert profesionales[0]["totalCalificaciones"] == 1

    def test_profesional_sin_calificaciones(self, svc, profesional):
        payload, _ = svc.mis_calificaciones(profesional.idUsuario)

        assert payload["promedio"] is None
        assert payload["total"] == 0

    def test_citas_del_paciente_traen_su_calificacion(self, svc, paciente, profesional):
        cita = _cita(paciente, profesional)
        svc.calificar_cita(paciente.idUsuario, cita.idCita, {"puntuacion": 5, "comentario": "Bien"})

        payload, _ = svc.list_patient_appointments(paciente.idUsuario)

        assert payload["citas"][0]["calificacion"] == {"puntuacion": 5, "comentario": "Bien"}


@pytest.mark.django_db
def test_flujo_por_la_api(client, paciente, profesional):
    cita = _cita(paciente, profesional)

    def login(email, rol):
        r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                        content_type="application/json")
        assert r.status_code == 200

    login("pac@test.com", "paciente")
    r = client.put(f"/api/citas/{cita.idCita}/calificacion", data=json.dumps({"puntuacion": 5, "comentario": "Gracias"}),
                   content_type="application/json")
    assert r.status_code == 200
    r = client.get("/api/profesionales")
    assert r.json()["profesionales"][0]["promedioCalificacion"] == 5.0

    login("pro@test.com", "profesional")
    r = client.get("/api/profesional/calificaciones")
    assert r.status_code == 200
    assert r.json()["calificaciones"][0]["comentario"] == "Gracias"
    r = client.put(f"/api/citas/{cita.idCita}/calificacion", data=json.dumps({"puntuacion": 1}),
                   content_type="application/json")
    assert r.status_code == 403
