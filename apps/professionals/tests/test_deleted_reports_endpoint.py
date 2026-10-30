import pytest
from django.test import Client

from apps.authentication.models import Register
from apps.professionals.models import PerfilProfesional, Reportes


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def create_user():
    def _create_user(user_id, role, **fields):
        return Register.objects.create(
            idUsuario=user_id,
            nombre=f"Test {role}",
            email=f"{role}{user_id}@test.com",
            password="test-hash",
            rol=role,
            **fields,
        )

    return _create_user


def authenticate_client(client, user):
    session = client.session
    session["idUsuario"] = user.idUsuario
    session["rol"] = user.rol
    session["nombre"] = user.nombre
    session.save()


@pytest.mark.django_db
def test_professional_sees_only_own_deleted_reports(client, create_user):
    professional = create_user(10, "profesional")
    other_professional = create_user(11, "profesional")
    PerfilProfesional.objects.create(idProfesional=professional, verificado=True)
    Reportes.objects.create(idProfesional=professional, tipoReporte="Propio", eliminado=True)
    Reportes.objects.create(
        idProfesional=other_professional, tipoReporte="Otro", eliminado=True
    )
    authenticate_client(client, professional)

    response = client.get("/api/reportes/eliminados")

    assert response.status_code == 200
    assert [row["tipoReporte"] for row in response.json()["reportes"]] == ["Propio"]


@pytest.mark.django_db
def test_admin_sees_all_deleted_reports(client, create_user):
    admin = create_user(1, "admin")
    professional = create_user(2, "profesional")
    Reportes.objects.create(idProfesional=admin, tipoReporte="Admin", eliminado=True)
    Reportes.objects.create(
        idProfesional=professional, tipoReporte="Profesional", eliminado=True
    )
    authenticate_client(client, admin)

    response = client.get("/api/reportes/eliminados")

    assert response.status_code == 200
    assert {row["tipoReporte"] for row in response.json()["reportes"]} == {
        "Admin",
        "Profesional",
    }


@pytest.mark.django_db
def test_patient_is_forbidden_from_deleted_reports(client, create_user):
    patient = create_user(20, "paciente")
    authenticate_client(client, patient)

    response = client.get("/api/reportes/eliminados")

    assert response.status_code == 403


@pytest.mark.django_db
def test_missing_session_is_forbidden_from_deleted_reports(client):
    response = client.get("/api/reportes/eliminados")

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("inactive_field", "inactive_value"),
    [("activo", False), ("estadoCuenta", "Suspendida")],
)
def test_inactive_account_is_forbidden_from_deleted_reports(
    client, create_user, inactive_field, inactive_value
):
    professional = create_user(
        30, "profesional", **{inactive_field: inactive_value}
    )
    authenticate_client(client, professional)

    response = client.get("/api/reportes/eliminados")

    assert response.status_code == 403
