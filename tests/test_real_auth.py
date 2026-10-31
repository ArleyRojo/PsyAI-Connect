import pytest
from django.test import Client
from django.contrib.auth import get_user_model


def _make_user(rol="paciente", email=None):
    User = get_user_model()
    email = email or f"{rol}_real@test.com"
    user = User.objects.create_user(
        email=email,
        nombre=f"Real {rol}",
        password="TestPass123",
        rol=rol,
    )
    if rol == "profesional":
        from apps.professionals.models import PerfilProfesional
        PerfilProfesional.objects.create(idProfesional=user, verificado=True)
    return user


def _auth_client(user):
    c = Client()
    s = c.session
    s["idUsuario"] = user.pk
    s["rol"] = user.rol
    s["nombre"] = user.nombre
    s.save()
    return c


@pytest.mark.django_db
class TestRealAuthAuthentication:
    def test_session_authenticated_vs_anonymous(self):
        user = _make_user("paciente", "real_auth@test.com")
        c = _auth_client(user)
        resp = c.get("/api/session")
        assert resp.status_code == 200
        assert resp.json()["logged_in"] is True
        resp2 = Client().get("/api/session")
        assert resp2.status_code == 200
        assert resp2.json()["logged_in"] is False


@pytest.mark.django_db
class TestRealAuthPatients:
    def test_profesionales_200_auth_403_anon(self):
        user = _make_user("paciente", "real_pat@test.com")
        assert Client().get("/api/profesionales").status_code == 401
        assert _auth_client(user).get("/api/profesionales").status_code == 200


@pytest.mark.django_db
class TestRealAuthProfessionals:
    def test_perfil_200_auth_403_anon(self):
        user = _make_user("profesional", "real_pro@test.com")
        url = f"/api/perfil/profesional/{user.pk}"
        assert Client().get(url).status_code == 401
        assert _auth_client(user).get(url).status_code == 200


@pytest.mark.django_db
class TestRealAuthScheduling:
    def test_citas_200_auth_403_anon(self):
        user = _make_user("paciente", "real_cita@test.com")
        assert Client().get("/api/citas/paciente").status_code == 401
        assert _auth_client(user).get("/api/citas/paciente").status_code == 200


@pytest.mark.django_db
class TestRealAuthChatbot:
    def test_config_200_auth_403_anon(self):
        user = _make_user("paciente", "real_chat@test.com")
        assert Client().get("/api/chatbot/config").status_code == 401
        assert _auth_client(user).get("/api/chatbot/config").status_code == 200


@pytest.mark.django_db
class TestRealAuthDocuments:
    def test_docs_200_auth_403_anon(self):
        user = _make_user("paciente", "real_doc@test.com")
        assert Client().get("/api/documentos/paciente").status_code == 401
        assert _auth_client(user).get("/api/documentos/paciente").status_code == 200


@pytest.mark.django_db
class TestRealAuthBilling:
    def test_facturas_200_auth_403_anon(self):
        user = _make_user("paciente", "real_bill@test.com")
        assert Client().get("/api/facturas").status_code == 401
        assert _auth_client(user).get("/api/facturas").status_code == 200


@pytest.mark.django_db
class TestRealAuthAdminPanel:
    def test_palabras_200_auth_403_anon(self):
        user = _make_user("admin", "real_adm@test.com")
        url = "/api/admin/chatbot-config/palabras-detectadas"
        assert Client().get(url).status_code == 401
        assert _auth_client(user).get(url).status_code == 200
