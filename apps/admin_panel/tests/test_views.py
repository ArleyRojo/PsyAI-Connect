import json
from unittest.mock import patch, MagicMock

import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from apps.admin_panel.views import (
    AdminUsuarioView,
    AdminNotificacionView,
    AdminLogsStreamView,
    AdminStatsStreamView,
)


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def mock_require_auth():
    with patch("apps.core.permissions.require_auth") as m:
        m.return_value = ({"idUsuario": 1, "rol": "admin", "nombre": "Test"}, None)
        yield m


# ── BUG 1: AdminUsuarioView.patch — validación de acción ───────────────────


class TestAdminUsuarioPatch:
    def test_patch_with_valid_action_suspender(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"accion": "suspender"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch("apps.admin_panel.views.admin_service") as mock_svc:
            mock_svc.block_user.return_value = (
                {"success": True, "message": "Usuario suspendido"},
                200,
            )
            resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["success"] is True
        mock_svc.block_user.assert_called_once()

    def test_patch_with_valid_action_reestablecer(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"accion": "reestablecer"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch("apps.admin_panel.views.admin_service") as mock_svc:
            mock_svc.block_user.return_value = (
                {"success": True, "message": "Usuario reestablecido"},
                200,
            )
            resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["success"] is True

    def test_patch_with_invalid_action_returns_400(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"accion": "accion_inexistente"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert data["success"] is False
        assert "inválida" in data["message"]

    def test_patch_without_action_or_rol_returns_400(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"campo_irrelevante": True}),
            content_type="application/json",
        )
        req.session = MagicMock()

        resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert data["success"] is False
        assert "no especificada" in data["message"]

    def test_patch_with_nuevoRol_calls_change_role(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"nuevoRol": "profesional"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch("apps.admin_panel.views.admin_service") as mock_svc:
            mock_svc.change_role.return_value = (
                {"success": True, "message": "Rol actualizado"},
                200,
            )
            resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 200
        mock_svc.change_role.assert_called_once()

    def test_patch_accion_takes_precedence_over_rol(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"accion": "suspender", "nuevoRol": "profesional"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch("apps.admin_panel.views.admin_service") as mock_svc:
            mock_svc.block_user.return_value = (
                {"success": True, "message": "Usuario suspendido"},
                200,
            )
            resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 200
        mock_svc.block_user.assert_called_once()
        mock_svc.change_role.assert_not_called()

    def test_patch_empty_body_returns_400(self, rf, mock_require_auth):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=b"",
            content_type="application/json",
        )
        req.session = MagicMock()

        resp = AdminUsuarioView.as_view()(req, id_usuario=1)

        assert resp.status_code == 400


# ── BUG 3: AdminNotificacionView.delete — orden de require_role ────────────


class TestAdminNotificacionDelete:
    def test_delete_requires_role_before_id_check(self, rf):
        req = rf.delete("/api/admin/notificaciones/1")
        req.session = MagicMock()

        with patch("apps.admin_panel.views.require_role") as mock_role:
            mock_role.return_value = (None, JsonResponse(
                {"success": False, "message": "No autorizado"}, status=403
            ))
            resp = AdminNotificacionView.as_view()(req, id_notificacion=1)

        assert resp.status_code == 403

    def test_delete_without_id_returns_400(self, rf, mock_require_auth):
        req = rf.delete("/api/admin/notificaciones/")
        req.session = MagicMock()

        resp = AdminNotificacionView.as_view()(req, id_notificacion=None)

        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert "Falta id" in data["message"]
