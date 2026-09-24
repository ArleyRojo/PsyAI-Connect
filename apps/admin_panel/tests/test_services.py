from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

from apps.admin_panel.services import AdminService


# ── AdminService.get_stats ────────────────────────────────────────────────────


class TestGetStats:
    def test_returns_stats(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_stats.return_value = {
            "usuarios": {"total": 100, "activos": 80, "suspendidos": 5},
            "notificaciones": {"total": 50},
            "citas_pendientes": 10,
            "logs_hoy": 25,
            "seguridad": {"fallos_login": 3, "actividad_sospechosa": 1},
            "timeline_seguridad": [],
        }
        with patch("apps.admin_panel.services.telemetry_service") as mock_tel:
            mock_tel.get_live_stats.return_value = {"cpu_percent": 50}
            payload, status = admin_service.get_stats()
            assert status == 200
            assert "stats" in payload


# ── AdminService.list_users ───────────────────────────────────────────────────


class TestListUsers:
    def test_returns_paginated(self, admin_service, mock_admin_repo):
        mock_admin_repo.list_users.return_value = [
            {"idUsuario": 1, "nombre": "Juan", "rol": "paciente"},
        ]
        payload, status = admin_service.list_users(page=1, limit=20)
        assert status == 200
        assert len(payload["usuarios"]) == 1


# ── AdminService.get_user ─────────────────────────────────────────────────────


class TestGetUser:
    def test_not_found(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_user.return_value = None
        payload, status = admin_service.get_user(999)
        assert status == 404

    def test_returns_user(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_user.return_value = {"idUsuario": 1, "nombre": "Juan"}
        payload, status = admin_service.get_user(1)
        assert status == 200
        assert payload["usuario"]["nombre"] == "Juan"


# ── AdminService.create_user ──────────────────────────────────────────────────


class TestCreateUser:
    def test_generates_temp_password_when_none(self, admin_service, mock_admin_repo):
        mock_admin_repo.create_user.return_value = 1
        payload, status = admin_service.create_user({
            "nombre": "Juan", "email": "new@test.com", "rol": "paciente",
        })
        assert status == 200
        assert payload["success"] is True
        assert "contrasena_temporal" in payload
        mock_admin_repo.create_user.assert_called_once()

    def test_uses_provided_password(self, admin_service, mock_admin_repo):
        mock_admin_repo.create_user.return_value = 1
        payload, status = admin_service.create_user({
            "nombre": "Juan", "email": "new@test.com", "contrasena": "Abc123", "rol": "paciente",
        })
        assert status == 200
        assert "contrasena_temporal" not in payload

    def test_duplicate_email_returns_400(self, admin_service, mock_admin_repo):
        mock_admin_repo.create_user.side_effect = ValueError("El email 'dup@test.com' ya está registrado")
        payload, status = admin_service.create_user({
            "nombre": "Juan", "email": "dup@test.com", "contrasena": "Abc123", "rol": "paciente",
        })
        assert status == 400
        assert payload["success"] is False
        assert "ya está registrado" in payload["message"]


# ── AdminService.update_user ──────────────────────────────────────────────────


class TestUpdateUser:
    def test_always_succeeds(self, admin_service, mock_admin_repo):
        payload, status = admin_service.update_user({"idUsuario": 1, "nombre": "Juan Updated"})
        assert status == 200
        assert payload["success"] is True
        mock_admin_repo.update_user.assert_called_once()


# ── AdminService.delete_user ──────────────────────────────────────────────────


class TestDeleteUser:
    def test_successful_delete(self, admin_service, mock_admin_repo):
        payload, status = admin_service.delete_user(1)
        assert status == 200
        assert payload["success"] is True
        mock_admin_repo.delete_user.assert_called_once_with(1)


# ── AdminService.block_user ───────────────────────────────────────────────────


class TestBlockUser:
    def test_suspend(self, admin_service, mock_admin_repo):
        mock_admin_repo.block_user.return_value = (0, {"nombre": "Test", "email": "test@test.com"})
        payload, status = admin_service.block_user({"idUsuario": 1, "accion": "bloquear"})
        assert status == 200
        assert "suspendido" in payload["message"]

    def test_restore(self, admin_service, mock_admin_repo):
        mock_admin_repo.block_user.return_value = (1, {"nombre": "Test", "email": "test@test.com"})
        payload, status = admin_service.block_user({"idUsuario": 1, "accion": "reestablecer"})
        assert status == 200
        assert "reestablecido" in payload["message"]


# ── AdminService.change_role ──────────────────────────────────────────────────


class TestChangeRole:
    def test_always_succeeds(self, admin_service, mock_admin_repo):
        payload, status = admin_service.change_role({"idUsuario": 1, "nuevoRol": "profesional"})
        assert status == 200
        assert payload["success"] is True
        mock_admin_repo.change_role.assert_called_once_with(1, "profesional")


# ── AdminService.notifications_feed ───────────────────────────────────────────


class TestNotificationsFeed:
    def test_returns_feed(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_notifications_feed.return_value = [
            {"titulo": "Nueva cita", "fecha": datetime(2025, 1, 15)},
        ]
        payload, status = admin_service.notifications_feed()
        assert status == 200
        assert len(payload["notificaciones"]) == 1
        assert "stats" in payload


# ── AdminService.create_notification ──────────────────────────────────────────


class TestCreateNotification:
    def test_always_succeeds(self, admin_service, mock_admin_repo):
        payload, status = admin_service.create_notification({
            "titulo": "Test", "mensaje": "Body", "tipo": "general", "destinatario": 1,
        })
        assert status == 200
        mock_admin_repo.create_notification.assert_called_once()


# ── AdminService.delete_notification ──────────────────────────────────────────


class TestDeleteNotification:
    def test_successful_delete(self, admin_service, mock_admin_repo):
        payload, status = admin_service.delete_notification(1)
        assert status == 200
        mock_admin_repo.delete_notification.assert_called_once_with(1)


# ── AdminService.get_logs ─────────────────────────────────────────────────────


class TestGetLogs:
    def test_returns_logs(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_logs.return_value = [
            {"accion": "login", "fecha": datetime(2025, 1, 15)},
        ]
        payload, status = admin_service.get_logs()
        assert status == 200
        assert len(payload["logs"]) == 1


# ── AdminService.role_history ─────────────────────────────────────────────────


class TestRoleHistory:
    def test_returns_history(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_role_history.return_value = [
            {"usuario_afectado": "Juan", "rol_anterior": "paciente", "rol_nuevo": "profesional"},
        ]
        payload, status = admin_service.role_history()
        assert status == 200
        assert len(payload["historial"]) == 1
        assert payload["historial"][0]["usuario"] == "Juan"


# ── AdminService.list_role_users ──────────────────────────────────────────────


class TestListRoleUsers:
    def test_returns_users(self, admin_service, mock_admin_repo):
        mock_admin_repo.list_role_users.return_value = [
            {"idUsuario": 1, "nombre": "Juan", "rol": "paciente"},
        ]
        payload, status = admin_service.list_role_users()
        assert status == 200
        assert len(payload["usuarios"]) == 1


# ── AdminService.get_chatbot_historial ────────────────────────────────────────


class TestGetChatbotHistorial:
    def test_returns_historial(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_chatbot_historial_rows.return_value = [
            {"nombre": "Juan", "nivelEmocionalDetectado": "Alto", "idPaciente": 1},
        ]
        mock_admin_repo.get_chatbot_historial_stats.return_value = {
            "total": 1, "alto": 1, "medio": 0, "bajo": 0,
        }
        payload, status = admin_service.get_chatbot_historial()
        assert status == 200
        assert len(payload["pacientes"]) == 1

    def test_filter_by_nivel(self, admin_service, mock_admin_repo):
        mock_admin_repo.get_chatbot_historial_rows.return_value = [
            {"nombre": "Juan", "nivelEmocionalDetectado": "Alto", "idPaciente": 1},
            {"nombre": "Maria", "nivelEmocionalDetectado": "Bajo", "idPaciente": 2},
        ]
        mock_admin_repo.get_chatbot_historial_stats.return_value = {
            "total": 2, "alto": 1, "medio": 0, "bajo": 1,
        }
        payload, status = admin_service.get_chatbot_historial(nivel="Alto")
        assert status == 200
        assert len(payload["pacientes"]) == 1
        assert payload["pacientes"][0]["nivel_max"] == "Alto"
