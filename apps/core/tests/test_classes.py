import pytest
from django.test import RequestFactory, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock

from apps.core.services import CoreService, core_service, subscribe_newsletter
from apps.core.notifier import NotificationService, notification_service
from apps.core.utils import (
    DateTimeHelper,
    FileValidator,
    AuthHelper,
    fmt_bogota,
    fmt_bogota_short,
    fmt_bogota_time,
    to_bogota,
    parse_bogota_datetime,
    validate_file_upload,
    get_current_user,
    require_auth,
    require_role,
)
from apps.core.views import (
    health_check,
    client_errors,
    serve_pages,
    notificacion_prueba,
    config_pago,
    theme_preference,
    newsletter_subscribe,
    HealthCheckView,
    ClientErrorsView,
    ServePagesView,
    NotificacionPruebaView,
    ConfigPagoView,
    ThemePreferenceView,
    NewsletterSubscribeView,
)


# ── DateTimeHelper ───────────────────────────────────────────────────────────


class TestDateTimeHelper:
    def test_fmt_bogota_naive_dt(self):
        from datetime import datetime
        dt = datetime(2026, 1, 15, 10, 30, 0)  # naive, asumir UTC
        resultado = DateTimeHelper.fmt_bogota(dt)
        # UTC 10:30 -> Bogotá 05:30 (UTC-5)
        assert resultado == "15/01/2026 05:30"

    def test_fmt_bogota_none(self):
        assert DateTimeHelper.fmt_bogota(None) == ""

    def test_fmt_bogota_short(self):
        from datetime import datetime
        dt = datetime(2026, 3, 5, 14, 0, 0)
        assert DateTimeHelper.fmt_bogota_short(dt) == "05/03/2026"

    def test_fmt_bogota_time(self):
        from datetime import datetime
        dt = datetime(2026, 3, 5, 14, 0, 0)
        assert DateTimeHelper.fmt_bogota_time(dt) == "09:00"

    def test_to_bogota(self):
        from datetime import datetime
        dt = datetime(2026, 6, 1, 12, 0, 0)
        resultado = DateTimeHelper.to_bogota(dt)
        assert resultado.hour == 7  # UTC 12:00 -> Bogotá 07:00

    def test_parse_bogota_datetime(self):
        resultado = DateTimeHelper.parse_bogota_datetime("2026-06-01T12:00")
        # Bogotá 12:00 -> UTC 17:00
        assert resultado.hour == 17

    def test_parse_bogota_datetime_empty(self):
        assert DateTimeHelper.parse_bogota_datetime("") is None
        assert DateTimeHelper.parse_bogota_datetime(None) is None


# ── FileValidator ────────────────────────────────────────────────────────────

class TestFileValidator:
    def test_extension_permitida(self):
        validator = FileValidator(allowed_extensions={"jpg", "pdf"}, use_magic_bytes=False)
        class _File:
            name = "documento.pdf"
            size = 1000
            def read(self, n=-1):
                return b""
            def seek(self, pos):
                pass
        nombre, error = validator.validate(_File())
        assert nombre == "documento.pdf"
        assert error is None

    def test_extension_rechazada(self):
        validator = FileValidator(allowed_extensions={"jpg", "pdf"})
        class _File:
            name = "documento.exe"
            size = 1000
            def read(self, n=-1):
                return b""
            def seek(self, pos):
                pass
        nombre, error = validator.validate(_File())
        assert nombre is None
        assert "no permitida" in error

    def test_archivo_demasiado_grande(self):
        validator = FileValidator(allowed_extensions={"jpg"}, max_size_mb=1)
        class _File:
            name = "foto.jpg"
            size = 2 * 1024 * 1024  # 2MB
            def read(self, n=-1):
                return b""
            def seek(self, pos):
                pass
        nombre, error = validator.validate(_File())
        assert nombre is None
        assert "excede el tamaño máximo" in error


# ── AuthHelper ───────────────────────────────────────────────────────────────


class TestAuthHelper:
    def test_get_current_user_sin_sesion(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.session = {}
        assert AuthHelper.get_current_user(request) is None

    def test_get_current_user_con_sesion(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.session = {
            "idUsuario": 5,
            "rol": "Profesional ",
            "nombre": "Dr. García",
        }
        user = AuthHelper.get_current_user(request)
        assert user is not None
        assert user["idUsuario"] == 5
        assert user["rol"] == "profesional"  # normalizado
        assert user["nombre"] == "Dr. García"

    def test_require_auth_sin_sesion(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.session = {}
        user, err = AuthHelper.require_auth(request)
        assert user is None
        assert err is not None
        assert err.status_code == 401

    @pytest.mark.django_db
    def test_require_role_rol_incorrecto(self):
        from apps.authentication.models import Register
        factory = RequestFactory()
        request = factory.get("/")
        request.session = {
            "idUsuario": 1,
            "rol": "paciente",
            "nombre": "Paciente",
        }
        # Crear usuario en BD para que require_auth lo encuentre
        Register.objects.create_user(
            idUsuario=1, email="pac@test.com", password="Pass123",
            rol="paciente", nombre="Paciente",
        )
        user, err = AuthHelper.require_role(request, "profesional")
        assert user is None
        assert err is not None
        assert err.status_code == 403

    @pytest.mark.django_db
    def test_require_role_rol_correcto(self):
        from apps.authentication.models import Register
        factory = RequestFactory()
        request = factory.get("/")
        request.session = {
            "idUsuario": 5,
            "rol": "profesional",
            "nombre": "Prof",
        }
        Register.objects.create_user(
            idUsuario=5, email="prof@test.com", password="Pass123",
            rol="profesional", nombre="Prof",
        )
        user, err = AuthHelper.require_role(request, "profesional")
        assert err is None
        assert user is not None
        assert user["rol"] == "profesional"


# ── CoreService ──────────────────────────────────────────────────────────────


class TestCoreService:
    @pytest.mark.django_db
    def test_subscribe_newsletter_valido(self):
        svc = CoreService()
        payload, status = svc.subscribe_newsletter("nuevo@test.com")
        assert status == 200
        assert payload["success"] is True
        assert payload["created"] is True

    @pytest.mark.django_db
    def test_subscribe_newsletter_invalido(self):
        svc = CoreService()
        payload, status = svc.subscribe_newsletter("no-es-un-email")
        assert status == 400
        assert payload["error"] == "Correo electronico invalido"

    @pytest.mark.django_db
    def test_subscribe_newsletter_vacio(self):
        svc = CoreService()
        payload, status = svc.subscribe_newsletter("")
        assert status == 400
        assert payload["error"] == "El correo es obligatorio"


# ── Aliases de compatibilidad ────────────────────────────────────────────────


class TestAliasCompatibilidad:
    def test_aliases_apuntan_a_metodos_de_clase(self):
        assert fmt_bogota == DateTimeHelper.fmt_bogota
        assert fmt_bogota_short == DateTimeHelper.fmt_bogota_short
        assert fmt_bogota_time == DateTimeHelper.fmt_bogota_time
        assert to_bogota == DateTimeHelper.to_bogota
        assert parse_bogota_datetime == DateTimeHelper.parse_bogota_datetime
        assert get_current_user == AuthHelper.get_current_user
        assert require_auth == AuthHelper.require_auth
        assert require_role == AuthHelper.require_role

    def test_core_service_alias(self):
        assert subscribe_newsletter == core_service.subscribe_newsletter
        _ = core_service.log_client_error  # noqa: F841

    def test_notifier_alias(self):
        _ = notification_service.notificar_paciente  # noqa: F841
        _ = notification_service.enviar_prueba  # noqa: F841


# ── Vistas de core ───────────────────────────────────────────────────────────


class TestCoreViews:
    def test_health_check_respond_200(self, db):
        factory = RequestFactory()
        request = factory.get("/health/")
        response = health_check(request)
        assert response.status_code == 200

    def test_urls_resuelven(self):
        """Verifica que los nombres de URL de core sigan resolviendo."""
        urls = [
            "core:health",
            "core:healthz",
            "core:notificacion-prueba",
            "core:config-pago",
        ]
        for nombre in urls:
            url = reverse(nombre)
            assert url is not None
            assert url.startswith("/")

    def test_clases_son_subclases_correctas(self):
        from django.views import View
        from rest_framework.views import APIView
        assert issubclass(HealthCheckView, APIView)
        assert issubclass(ClientErrorsView, APIView)
        assert issubclass(ServePagesView, View)
        assert issubclass(NotificacionPruebaView, APIView)
        assert issubclass(ConfigPagoView, APIView)
        assert issubclass(ThemePreferenceView, APIView)
        assert issubclass(NewsletterSubscribeView, APIView)

    def test_health_check_via_as_view(self, db):
        factory = RequestFactory()
        request = factory.get("/health/")
        response = HealthCheckView.as_view()(request)
        assert response.status_code == 200

    def test_config_pago_via_as_view(self, settings):
        settings.PAGO_CUENTA_URL = ""
        settings.PAGO_CUENTA_NOMBRE = ""
        factory = RequestFactory()
        request = factory.get("/api/config/pago/")
        response = ConfigPagoView.as_view()(request)
        assert response.status_code == 200
