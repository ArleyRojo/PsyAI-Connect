from datetime import timedelta

import pytest
from django.utils import timezone

from apps.authentication.models import Register, RecoveryTokens
from apps.authentication.repositories import AuthRepository


@pytest.mark.django_db
class TestUserExistsByEmail:
    def test_returns_false_for_nonexistent(self):
        repo = AuthRepository()
        assert repo.user_exists_by_email("noexist@test.com") is False

    def test_returns_true_for_existing(self):
        Register.objects.create_user(
            email="exists@test.com",
            nombre="Test",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        assert repo.user_exists_by_email("exists@test.com") is True


@pytest.mark.django_db
class TestCreateUser:
    def test_creates_user_and_returns_id(self):
        repo = AuthRepository()
        user_id = repo.create_user(
            nombre="New User",
            email="new@test.com",
            password_hash="hashed_password",
            rol="paciente",
        )
        assert user_id is not None
        user = Register.objects.get(idUsuario=user_id)
        assert user.email == "new@test.com"
        assert user.nombre == "New User"
        assert user.rol == "paciente"


@pytest.mark.django_db
class TestGetUserByEmail:
    def test_returns_dict_for_existing_active_user(self):
        Register.objects.create_user(
            email="active@test.com",
            nombre="Active User",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        result = repo.get_user_by_email("active@test.com")
        assert result is not None
        assert result["email"] == "active@test.com"
        assert result["nombre"] == "Active User"
        assert "idUsuario" in result
        assert "contrasena" in result

    def test_returns_none_for_nonexistent(self):
        repo = AuthRepository()
        assert repo.get_user_by_email("ghost@test.com") is None

    def test_returns_none_for_suspended_account(self):
        user = Register.objects.create_user(
            email="suspended@test.com",
            nombre="Suspended",
            password="Abc123",
            rol="paciente",
        )
        user.estadoCuenta = "Suspendida"
        user.save()
        repo = AuthRepository()
        assert repo.get_user_by_email("suspended@test.com") is None

    def test_admin_only_filter(self):
        Register.objects.create_user(
            email="pac@test.com",
            nombre="Paciente",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        assert repo.get_user_by_email("pac@test.com", admin_only=True) is None

        Register.objects.create_user(
            email="adm@test.com",
            nombre="Admin",
            password="Abc123",
            rol="admin",
        )
        assert repo.get_user_by_email("adm@test.com", admin_only=True) is not None


@pytest.mark.django_db
class TestActiveUserExistsByEmail:
    def test_true_for_active_user(self):
        Register.objects.create_user(
            email="active@test.com",
            nombre="Active",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        assert repo.active_user_exists_by_email("active@test.com") is True

    def test_false_for_nonexistent(self):
        repo = AuthRepository()
        assert repo.active_user_exists_by_email("noexist@test.com") is False

    def test_false_for_suspended_user(self):
        user = Register.objects.create_user(
            email="suspended@test.com",
            nombre="Suspended",
            password="Abc123",
            rol="paciente",
        )
        user.estadoCuenta = "Suspendida"
        user.save()
        repo = AuthRepository()
        assert repo.active_user_exists_by_email("suspended@test.com") is False


@pytest.mark.django_db
class TestRecoveryTokenFlow:
    def test_create_and_validate_token(self):
        user = Register.objects.create_user(
            email="recover@test.com",
            nombre="Recover",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        token = "test_token_abc"
        expires = timezone.now() + timedelta(hours=1)

        repo.create_password_recovery_token("recover@test.com", token, expires)

        user_id = repo.validate_recovery_token(token)
        assert user_id == user.idUsuario

    def test_validate_expired_token(self):
        Register.objects.create_user(
            email="expired@test.com",
            nombre="Expired",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        token = "expired_token"
        expires = timezone.now() - timedelta(hours=1)

        repo.create_password_recovery_token("expired@test.com", token, expires)

        assert repo.validate_recovery_token(token) is None

    def test_validate_nonexistent_token(self):
        repo = AuthRepository()
        assert repo.validate_recovery_token("bogus_token") is None


@pytest.mark.django_db
class TestInvalidateRecoveryToken:
    def test_invalidates_token(self):
        Register.objects.create_user(
            email="inv@test.com",
            nombre="Inv",
            password="Abc123",
            rol="paciente",
        )
        repo = AuthRepository()
        token = "invalidate_me"
        expires = timezone.now() + timedelta(hours=1)

        repo.create_password_recovery_token("inv@test.com", token, expires)
        assert repo.validate_recovery_token(token) is not None

        repo.invalidate_recovery_token(token)
        assert repo.validate_recovery_token(token) is None

    def test_invalidate_nonexistent_returns_false(self):
        repo = AuthRepository()
        assert repo.invalidate_recovery_token("no_such_token") is False


@pytest.mark.django_db
class TestUpdatePassword:
    def test_updates_password(self):
        user = Register.objects.create_user(
            email="update@test.com",
            nombre="Update",
            password="OldPass1",
            rol="paciente",
        )
        old_hash = user.contrasena
        repo = AuthRepository()

        result = repo.update_password(user.idUsuario, "new_hash_abc")
        assert result is True

        user.refresh_from_db()
        assert user.contrasena == "new_hash_abc"
        assert user.contrasena != old_hash

    def test_update_nonexistent_user_returns_false(self):
        repo = AuthRepository()
        assert repo.update_password(99999, "hash") is False
