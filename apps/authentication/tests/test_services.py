from unittest.mock import MagicMock, patch

import pytest

from apps.authentication.services import AuthService, ValidationError, Validator


# ── Validator unit tests ─────────────────────────────────────────────────────


class TestValidatorRequired:
    def test_raises_on_none(self):
        with pytest.raises(ValidationError, match="requerido"):
            Validator.required(None, "campo")

    def test_raises_on_empty_string(self):
        with pytest.raises(ValidationError, match="requerido"):
            Validator.required("", "campo")

    def test_returns_value(self):
        assert Validator.required("hola", "campo") == "hola"


class TestValidatorEmail:
    def test_valid_email(self):
        assert Validator.email("test@example.com") == "test@example.com"

    def test_strips_and_lowercases(self):
        assert Validator.email("User@Example.Com") == "user@example.com"

    def test_invalid_format(self):
        with pytest.raises(ValidationError, match="inválido"):
            Validator.email("not-an-email")

    def test_missing_at(self):
        with pytest.raises(ValidationError):
            Validator.email("testexample.com")


class TestValidatorPassword:
    def test_valid_password(self):
        assert Validator.password("Abc123") == "Abc123"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="6 caracteres"):
            Validator.password("Ab1")

    def test_no_uppercase(self):
        with pytest.raises(ValidationError, match="mayúscula"):
            Validator.password("abc123")

    def test_no_number(self):
        with pytest.raises(ValidationError, match="número"):
            Validator.password("Abcdef")

    def test_empty(self):
        with pytest.raises(ValidationError, match="requerida"):
            Validator.password("")


class TestValidatorRole:
    def test_valid_role(self):
        assert Validator.role("paciente") == "paciente"

    def test_invalid_role(self):
        with pytest.raises(ValidationError, match="inválido"):
            Validator.role("hacker")


class TestValidatorPositiveInteger:
    def test_valid(self):
        assert Validator.positive_integer(5, "count") == 5

    def test_string_number(self):
        assert Validator.positive_integer("10", "count") == 10

    def test_zero(self):
        with pytest.raises(ValidationError, match="positivo"):
            Validator.positive_integer(0, "count")

    def test_negative(self):
        with pytest.raises(ValidationError, match="positivo"):
            Validator.positive_integer(-1, "count")

    def test_not_a_number(self):
        with pytest.raises(ValidationError, match="entero"):
            Validator.positive_integer("abc", "count")


# ── AuthService.register_user tests ──────────────────────────────────────────


@pytest.mark.django_db
class TestRegisterUser:
    def test_missing_nombre(self, auth_service):
        payload, status = auth_service.register_user({
            "email": "test@test.com",
            "password": "Abc123",
            "confirm_password": "Abc123",
            "rol": "paciente",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 400
        assert payload["success"] is False
        assert "nombre" in payload["message"].lower()

    def test_missing_email(self, auth_service):
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "password": "Abc123",
            "confirm_password": "Abc123",
            "rol": "paciente",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 400
        assert payload["success"] is False

    def test_invalid_email(self, auth_service):
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "email": "bad-email",
            "password": "Abc123",
            "confirm_password": "Abc123",
            "rol": "paciente",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 400
        assert payload["success"] is False

    def test_weak_password(self, auth_service):
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "email": "test@test.com",
            "password": "123",
            "confirm_password": "123",
            "rol": "paciente",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 400
        assert payload["success"] is False

    def test_password_mismatch(self, auth_service):
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "email": "test@test.com",
            "password": "Abc123",
            "confirm_password": "Xyz789",
            "rol": "paciente",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 400
        assert "coinciden" in payload["message"].lower()

    def test_missing_genero(self, auth_service):
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "email": "test@test.com",
            "password": "Abc123",
            "confirm_password": "Abc123",
            "rol": "paciente",
            "acepta_terminos": True,
        })
        assert status == 400
        assert "género" in payload["message"].lower()

    def test_invalid_rol(self, auth_service):
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "email": "test@test.com",
            "password": "Abc123",
            "confirm_password": "Abc123",
            "rol": "hacker",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 400

    def test_duplicate_email(self, auth_service, mock_auth_repo):
        mock_auth_repo.user_exists_by_email.return_value = True
        payload, status = auth_service.register_user({
            "nombre": "Test",
            "email": "dup@test.com",
            "password": "Abc123",
            "confirm_password": "Abc123",
            "rol": "paciente",
            "genero": "M",
            "acepta_terminos": True,
        })
        assert status == 409
        assert payload["success"] is False

    def test_successful_registration(self, auth_service, mock_auth_repo):
        mock_auth_repo.user_exists_by_email.return_value = False
        mock_auth_repo.create_user.return_value = 1

        with patch("apps.authentication.models.ConsentimientoUsuario.objects.create") as mock_consent:
            payload, status = auth_service.register_user({
                "nombre": "Test User",
                "email": "new@test.com",
                "password": "Abc123",
                "confirm_password": "Abc123",
                "rol": "paciente",
                "genero": "F",
                "edad": 25,
                "acepta_terminos": True,
            })
        assert status == 201
        assert payload["success"] is True
        mock_auth_repo.create_user.assert_called_once()
        mock_consent.assert_called_once()


# ── AuthService.login_user tests ─────────────────────────────────────────────


class TestLoginUser:
    def test_missing_email(self, auth_service):
        payload, status, session = auth_service.login_user({}, "127.0.0.1")
        assert status == 400
        assert payload["success"] is False

    def test_missing_password(self, auth_service):
        payload, status, session = auth_service.login_user(
            {"email": "test@test.com"}, "127.0.0.1"
        )
        assert status == 400
        assert payload["success"] is False

    def test_brute_force_blocked(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (True, 600)
        payload, status, session = auth_service.login_user(
            {"email": "test@test.com", "password": "Abc123"}, "127.0.0.1"
        )
        assert status == 429
        assert "bloqueada" in payload["message"].lower()

    def test_user_not_found(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (False, 0)
        auth_service.repo.get_user_by_email.return_value = None

        payload, status, session = auth_service.login_user(
            {"email": "noexist@test.com", "password": "Abc123"}, "127.0.0.1"
        )
        assert status == 401
        assert payload["success"] is False

    def test_wrong_role(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (False, 0)
        auth_service.repo.get_user_by_email.return_value = {
            "idUsuario": 1,
            "email": "test@test.com",
            "nombre": "Test",
            "rol": "paciente",
            "contrasena": "hashed",
            "estadoCuenta": "Activa",
        }

        payload, status, session = auth_service.login_user(
            {"email": "test@test.com", "password": "Abc123", "rol": "admin"},
            "127.0.0.1",
        )
        assert status == 403

    def test_wrong_password(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (False, 0)
        auth_service.repo.get_user_by_email.return_value = {
            "idUsuario": 1,
            "email": "test@test.com",
            "nombre": "Test",
            "rol": "paciente",
            "contrasena": "wrong_hash",
            "estadoCuenta": "Activa",
        }

        with patch("apps.authentication.services.SecurityHelper") as mock_sec:
            mock_sec.verify_password.return_value = False
            mock_sec.is_sha256_hash.return_value = True
            payload, status, session = auth_service.login_user(
                {"email": "test@test.com", "password": "WrongPass1"}, "127.0.0.1"
            )
        assert status == 401
        assert payload["success"] is False
        auth_service.security_repo.register_failed_attempt.assert_called_once()

    def test_successful_login(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (False, 0)
        auth_service.repo.get_user_by_email.return_value = {
            "idUsuario": 1,
            "email": "test@test.com",
            "nombre": "Test User",
            "rol": "paciente",
            "contrasena": "correct_hash",
            "estadoCuenta": "Activa",
            "fotoPerfil": None,
        }

        with patch("apps.authentication.services.SecurityHelper") as mock_sec:
            mock_sec.verify_password.return_value = True
            mock_sec.is_sha256_hash.return_value = True
            payload, status, session = auth_service.login_user(
                {"email": "test@test.com", "password": "Abc123"}, "127.0.0.1"
            )
        assert status == 200
        assert payload["success"] is True
        assert session is not None
        assert session["rol"] == "paciente"
        auth_service.security_repo.reset_failed_attempts.assert_called_once()

    def test_suspended_user_cannot_login(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (False, 0)
        auth_service.repo.get_user_by_email.return_value = {
            "idUsuario": 1,
            "email": "suspended@test.com",
            "nombre": "Suspended User",
            "rol": "paciente",
            "contrasena": "correct_hash",
            "estadoCuenta": "Suspendida",
            "activo": False,
            "fotoPerfil": None,
        }

        with patch("apps.authentication.services.SecurityHelper") as mock_sec:
            mock_sec.verify_password.return_value = True
            mock_sec.is_sha256_hash.return_value = True
            payload, status, session = auth_service.login_user(
                {"email": "suspended@test.com", "password": "Abc123"}, "127.0.0.1"
            )
        assert status == 403
        assert payload["success"] is False
        assert "suspendida" in payload["message"].lower()
        assert session is None

    def test_activo_false_with_activa_estado_rejected(self, auth_service, mock_security_repo):
        mock_security_repo.check_brute_force.return_value = (False, 0)
        auth_service.repo.get_user_by_email.return_value = {
            "idUsuario": 1,
            "email": "inconsistent@test.com",
            "nombre": "Inconsistent User",
            "rol": "paciente",
            "contrasena": "correct_hash",
            "estadoCuenta": "Activa",
            "activo": False,
            "fotoPerfil": None,
        }

        with patch("apps.authentication.services.SecurityHelper") as mock_sec:
            mock_sec.verify_password.return_value = True
            mock_sec.is_sha256_hash.return_value = True
            payload, status, session = auth_service.login_user(
                {"email": "inconsistent@test.com", "password": "Abc123"}, "127.0.0.1"
            )
        assert status == 403
        assert payload["success"] is False
        assert "suspendida" in payload["message"].lower()
        assert session is None


# ── AuthService.recover_password tests ───────────────────────────────────────


class TestRecoverPassword:
    def test_missing_email(self, auth_service):
        payload, status = auth_service.recover_password("")
        assert status == 400
        assert payload["success"] is False

    def test_invalid_email(self, auth_service):
        payload, status = auth_service.recover_password("not-email")
        assert status == 400

    def test_nonexistent_email(self, auth_service, mock_auth_repo):
        mock_auth_repo.active_user_exists_by_email.return_value = False
        payload, status = auth_service.recover_password("noexist@test.com")
        assert status == 404
        assert payload["success"] is False

    @patch("apps.authentication.services.MailService.send_recovery_email")
    def test_existing_email_sends_token(self, mock_mail, auth_service, mock_auth_repo):
        mock_auth_repo.active_user_exists_by_email.return_value = True
        mock_mail.return_value = True
        mock_request = MagicMock()
        mock_request.get_host.return_value = "localhost"
        mock_request.scheme = "http"

        payload, status = auth_service.recover_password(
            "user@test.com", request=mock_request
        )
        assert status == 200
        assert payload["success"] is True
        mock_auth_repo.create_password_recovery_token.assert_called_once()


# ── AuthService.reset_password tests ─────────────────────────────────────────


class TestResetPassword:
    def test_missing_token(self, auth_service):
        payload, status = auth_service.reset_password({
            "new_password": "Abc123",
            "confirm_password": "Abc123",
        })
        assert status == 400
        assert "token" in payload["message"].lower()

    def test_invalid_token(self, auth_service, mock_auth_repo):
        mock_auth_repo.validate_recovery_token.return_value = None
        payload, status = auth_service.reset_password({
            "token": "bad_token",
            "new_password": "Abc123",
            "confirm_password": "Abc123",
        })
        assert status == 400
        assert "inválido" in payload["message"].lower()

    def test_password_mismatch(self, auth_service, mock_auth_repo):
        mock_auth_repo.validate_recovery_token.return_value = 1
        payload, status = auth_service.reset_password({
            "token": "valid_token",
            "new_password": "Abc123",
            "confirm_password": "Xyz789",
        })
        assert status == 400
        assert "coinciden" in payload["message"].lower()

    def test_successful_reset(self, auth_service, mock_auth_repo):
        mock_auth_repo.validate_recovery_token.return_value = 1
        payload, status = auth_service.reset_password({
            "token": "valid_token",
            "new_password": "NewPass1",
            "confirm_password": "NewPass1",
        })
        assert status == 200
        assert payload["success"] is True
        mock_auth_repo.invalidate_recovery_token.assert_called_once()
        mock_auth_repo.update_password.assert_called_once()
