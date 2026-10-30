import pytest
from unittest.mock import patch, MagicMock

from apps.admin_panel.repositories import AdminRepository


# ── BUG 5: AdminRepository.create_user — sin contraseña ────────────────────


class TestRepositoryCreateUser:
    def test_raises_valueerror_when_no_password(self):
        repo = AdminRepository()
        with pytest.raises(ValueError, match="contraseña es requerida"):
            repo.create_user({
                "nombre": "Test",
                "email": "test@test.com",
                "rol": "paciente",
            })

    def test_raises_valueerror_when_password_is_none(self):
        repo = AdminRepository()
        with pytest.raises(ValueError, match="contraseña es requerida"):
            repo.create_user({
                "nombre": "Test",
                "email": "test@test.com",
                "contrasena": None,
                "rol": "paciente",
            })

    def test_raises_valueerror_when_password_is_empty_string(self):
        repo = AdminRepository()
        with pytest.raises(ValueError, match="contraseña es requerida"):
            repo.create_user({
                "nombre": "Test",
                "email": "test@test.com",
                "contrasena": "",
                "rol": "paciente",
            })

    @pytest.mark.django_db
    @patch("apps.admin_panel.repositories.Register")
    @patch("apps.authentication.security.SecurityHelper.hash_password")
    @patch("apps.admin_panel.repositories.AdminRepository.registrar_log")
    def test_creates_user_when_password_provided(self, mock_log, mock_hash_password, mock_register):
        repo = AdminRepository()
        mock_register.DoesNotExist = type("DoesNotExist", (), {})
        mock_register.objects.filter.return_value.exists.return_value = False
        mock_register.return_value.save = MagicMock()
        mock_register.return_value.idUsuario = 1
        mock_hash_password.return_value = "hashed_pw"

        repo.create_user({
            "nombre": "Test",
            "email": "test@test.com",
            "contrasena": "Secure123!",
            "rol": "admin",
        })

        mock_hash_password.assert_called_once_with("Secure123!")
        mock_register.return_value.save.assert_called_once()

    @patch("apps.admin_panel.repositories.Register")
    def test_raises_valueerror_when_email_duplicate(self, mock_register):
        repo = AdminRepository()
        mock_register.objects.filter.return_value.exists.return_value = True
        with pytest.raises(ValueError, match="ya está registrado"):
            repo.create_user({
                "nombre": "Test",
                "email": "dup@test.com",
                "contrasena": "Secure123!",
                "rol": "paciente",
            })


# ── BUG 4: Cache behavior ─────────────────────────────────────────────────


class TestStatsCache:
    def test_uses_django_cache(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_stats.return_value = {"total_usuarios": 10}

        with patch("apps.admin_panel.services.cache") as mock_cache:
            mock_cache.get.return_value = None
            with patch("apps.admin_panel.services.telemetry_service") as mock_tel:
                mock_tel.get_live_stats.return_value = {"cpu": 5}
                payload, status = admin_service.get_stats()

            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert call_args[0][0] == "admin_panel:stats"
            assert call_args[0][2] == 10  # TTL

    def test_returns_cached_when_available(self, admin_service, mock_admin_repo):
        cached = ({"success": True, "stats": {"cached": True}}, 200)

        with patch("apps.admin_panel.services.cache") as mock_cache:
            mock_cache.get.return_value = cached
            payload, status = admin_service.get_stats()

        assert payload["stats"]["cached"] is True
        mock_admin_repo.get_stats.assert_not_called()

    def test_force_bypasses_cache(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_stats.return_value = {"total_usuarios": 5}

        with patch("apps.admin_panel.services.cache") as mock_cache:
            mock_cache.get.return_value = ({"success": True, "stats": {"old": True}}, 200)
            with patch("apps.admin_panel.services.telemetry_service") as mock_tel:
                mock_tel.get_live_stats.return_value = {"cpu": 3}
                payload, status = admin_service.get_stats(force=True)

        mock_admin_repo.get_stats.assert_called_once()
        mock_cache.get.assert_not_called()
