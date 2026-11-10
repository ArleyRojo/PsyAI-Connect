"""Pruebas de asignación y reasignación de casos por el administrador (HU-57 / HU-58)."""
import json
from datetime import date, time, timedelta

import pytest
from django.core import mail

from apps.admin_panel.models import Logs
from apps.authentication.models import Register
from apps.authentication.security import SecurityHelper
from apps.documents.models import DocumentosClinicos
from apps.patients.models import Anamnesis
from apps.professionals import asignaciones
from apps.professionals.models import (
    ConsejoPaciente, Diagnostico, PacientesProfesional, PerfilProfesional, ReasignacionCaso, Reportes,
)
from apps.professionals.repositories import ProfessionalRepository
from apps.scheduling.models import Citas, Notificaciones


def _usuario(email, rol, nombre):
    return Register.objects.create(
        nombre=nombre, email=email, contrasena=SecurityHelper.hash_password("Clave123*"),
        rol=rol, activo=True, estadoCuenta="Activa",
    )


def _profesional(email, nombre, verificado=True):
    user = _usuario(email, "profesional", nombre)
    PerfilProfesional.objects.create(idProfesional=user, verificado=verificado, especialidad="Clínica")
    return user


@pytest.fixture
def paciente():
    return _usuario("pac@test.com", "paciente", "Juan Pérez")


@pytest.fixture
def anterior():
    return _profesional("ruiz@test.com", "Dra. Ruiz")


@pytest.fixture
def nuevo():
    return _profesional("gomez@test.com", "Dr. Gómez")


@pytest.fixture
def caso(paciente, anterior):
    """Paciente con historial completo y citas con el profesional anterior."""
    asignacion = PacientesProfesional.objects.create(idProfesional=anterior, idPaciente=paciente)
    Diagnostico.objects.create(idAsignacion=asignacion, diagnostico="Ansiedad leve")
    ConsejoPaciente.objects.create(idAsignacion=asignacion, titulo="Respirar", descripcion="4-7-8")
    Anamnesis.objects.create(idPaciente=paciente, idProfesional=anterior)
    DocumentosClinicos.objects.create(
        idPaciente=paciente, idProfesional=anterior, nombreArchivo="informe.pdf", rutaArchivo="x/informe.pdf",
    )
    Reportes.objects.create(idPaciente=paciente, idProfesional=anterior, tipoReporte="Seguimiento")
    hoy = date.today()
    for dias, estado in ((3, "Pendiente"), (5, "Confirmada"), (-3, "Completada")):
        Citas.objects.create(
            idPaciente=paciente, idProfesional=anterior, fecha=hoy + timedelta(days=dias), hora=time(9, 0),
            tipoCita="Virtual", motivo="Control", estado=estado,
        )
    return asignacion


def _datos(paciente, anterior, nuevo, motivo="Cambio de horario del paciente"):
    return {"idPaciente": paciente.idUsuario, "idProfesionalAnterior": anterior.idUsuario,
            "idProfesionalNuevo": nuevo.idUsuario, "motivo": motivo}


@pytest.mark.django_db
class TestReasignar:
    def test_pasa_todo_el_historial_al_nuevo(self, paciente, anterior, nuevo, caso):
        payload, status = asignaciones.reasignar(_datos(paciente, anterior, nuevo), "Admin Demo")

        assert status == 200, payload
        asignacion = PacientesProfesional.objects.get(idPaciente=paciente)
        assert asignacion.idProfesional == nuevo
        assert Diagnostico.objects.get().idAsignacion == asignacion
        assert ConsejoPaciente.objects.get().idAsignacion == asignacion
        assert Anamnesis.objects.get().idProfesional == nuevo
        assert DocumentosClinicos.objects.get().idProfesional == nuevo
        assert Reportes.objects.get().idProfesional == nuevo

    def test_el_anterior_pierde_el_acceso(self, paciente, anterior, nuevo, caso):
        asignaciones.reasignar(_datos(paciente, anterior, nuevo))

        repo = ProfessionalRepository()
        assert repo.professional_has_patient(nuevo.idUsuario, paciente.idUsuario)
        assert not repo.professional_has_patient(anterior.idUsuario, paciente.idUsuario)

    def test_cancela_solo_las_citas_futuras(self, paciente, anterior, nuevo, caso):
        payload, _ = asignaciones.reasignar(_datos(paciente, anterior, nuevo))

        assert payload["registro"]["citasCanceladas"] == 2
        estados = sorted(Citas.objects.values_list("estado", flat=True))
        assert estados == ["Cancelada", "Cancelada", "Completada"]
        assert Citas.objects.filter(estado="Cancelada").first().motivoCancelacion == "Caso reasignado a Dr. Gómez"

    def test_registra_y_avisa_a_los_tres(self, paciente, anterior, nuevo, caso):
        asignaciones.reasignar(_datos(paciente, anterior, nuevo), "Admin Demo")

        registro = ReasignacionCaso.objects.get()
        assert registro.idProfesionalAnterior == anterior and registro.idProfesionalNuevo == nuevo
        assert registro.administrador == "Admin Demo"
        assert Logs.objects.filter(modulo="Asignaciones", accion="Reasignar caso").exists()
        avisados = set(Notificaciones.objects.filter(canal="interno", tipo="Asignacion")
                       .values_list("idUsuario_id", flat=True))
        assert avisados == {paciente.idUsuario, anterior.idUsuario, nuevo.idUsuario}
        destinatarios = {d for m in mail.outbox for d in m.to}
        assert {"ruiz@test.com", "gomez@test.com"} <= destinatarios

    def test_si_el_nuevo_ya_lo_atendia_se_unen_los_registros(self, paciente, anterior, nuevo, caso):
        PacientesProfesional.objects.create(idProfesional=nuevo, idPaciente=paciente)

        _, status = asignaciones.reasignar(_datos(paciente, anterior, nuevo))

        assert status == 200
        asignacion = PacientesProfesional.objects.get(idPaciente=paciente)
        assert asignacion.idProfesional == nuevo
        assert Diagnostico.objects.get().idAsignacion == asignacion

    def test_profesional_nuevo_sin_verificar(self, paciente, anterior, caso):
        sin_verificar = _profesional("nuevo@test.com", "Sin verificar", verificado=False)

        _, status = asignaciones.reasignar(_datos(paciente, anterior, sin_verificar))

        assert status == 400
        assert PacientesProfesional.objects.get(idPaciente=paciente).idProfesional == anterior

    @pytest.mark.parametrize("motivo", ["", "corto", "x" * 501])
    def test_motivo_obligatorio(self, paciente, anterior, nuevo, caso, motivo):
        if motivo == "corto":
            motivo = "abc"
        _, status = asignaciones.reasignar(_datos(paciente, anterior, nuevo, motivo))

        assert status == 400
        assert not ReasignacionCaso.objects.exists()

    def test_mismo_profesional(self, paciente, anterior, caso):
        _, status = asignaciones.reasignar(_datos(paciente, anterior, anterior))

        assert status == 400

    def test_paciente_no_asignado_a_ese_profesional(self, paciente, anterior, nuevo):
        _, status = asignaciones.reasignar(_datos(paciente, anterior, nuevo))

        assert status == 400


@pytest.mark.django_db
class TestAsignar:
    def test_asigna_paciente_sin_profesional(self, paciente, nuevo):
        payload, status = asignaciones.asignar(
            {"idPaciente": paciente.idUsuario, "idProfesional": nuevo.idUsuario, "motivo": "Primera consulta"},
        )

        assert status == 201, payload
        assert PacientesProfesional.objects.filter(idPaciente=paciente, idProfesional=nuevo).exists()
        assert ReasignacionCaso.objects.get().to_dict()["tipo"] == "Asignación"

    def test_no_duplica(self, paciente, nuevo):
        PacientesProfesional.objects.create(idProfesional=nuevo, idPaciente=paciente)

        _, status = asignaciones.asignar(
            {"idPaciente": paciente.idUsuario, "idProfesional": nuevo.idUsuario, "motivo": "Primera consulta"},
        )

        assert status == 400
        assert PacientesProfesional.objects.count() == 1


@pytest.mark.django_db
def test_listado_trae_profesionales_y_citas_futuras(paciente, anterior, nuevo, caso):
    payload, _ = asignaciones.listar_asignaciones()

    fila = next(p for p in payload["pacientes"] if p["idPaciente"] == paciente.idUsuario)
    assert fila["profesionales"] == [{
        "idProfesional": anterior.idUsuario, "nombre": "Dra. Ruiz",
        "desde": fila["profesionales"][0]["desde"], "citasFuturas": 2,
    }]
    assert {p["nombre"] for p in payload["profesionales"]} == {"Dra. Ruiz", "Dr. Gómez"}


@pytest.mark.django_db
def test_api_solo_admin_y_aviso_en_la_campana_del_profesional(client, paciente, anterior, nuevo, caso):
    def login(email, rol):
        r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                        content_type="application/json")
        assert r.status_code == 200

    login("ruiz@test.com", "profesional")
    assert client.get("/api/admin/asignaciones").status_code == 403

    _usuario("admin@test.com", "admin", "Admin Demo")
    login("admin@test.com", "admin")
    assert client.get("/api/admin/asignaciones").status_code == 200
    r = client.post("/api/admin/asignaciones/reasignar", data=json.dumps(_datos(paciente, anterior, nuevo)),
                    content_type="application/json")
    assert r.status_code == 200
    assert client.get("/api/admin/asignaciones/historial").json()["historial"][0]["administrador"] == "Admin Demo"

    login("gomez@test.com", "profesional")
    alertas = client.get("/api/profesional/dashboard").json()
    textos = json.dumps(alertas, ensure_ascii=False)
    assert "Nuevo paciente reasignado" in textos
