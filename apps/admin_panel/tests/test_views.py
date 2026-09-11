import json
from unittest.mock import patch, MagicMock

import pytest
from rest_framework.test import APIRequestFactory
from rest_framework import status

from apps.admin_panel.views import (
    AdminUsuarioViewSet,
    AdminNotificacionAPIView,
    AdminLogsStreamAPIView,
    AdminStatsStreamAPIView,
    AdminChatbotConfigViewSet,
    AdminChatbotPalabrasAPIView,
)
from apps.core.permissions import IsAuthenticatedDRF


@pytest.fixture
def rf():
    return APIRequestFactory()


def _auth_admin(_self, request, view):
    request.user_id = 1
    request.user_role = "admin"
    request.user_name = "Test"
    return True


@pytest.fixture
def mock_auth_admin():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
        yield


@pytest.fixture
def mock_require_auth():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
        yield


@pytest.fixture
def mock_require_admin():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
        yield


# ── BUG 1: AdminUsuarioView.patch — validación de acción ───────────────────


class TestAdminUsuarioPatch:
    def test_patch_with_valid_action_suspender(self, rf, mock_auth_admin):
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
            view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
            resp = view(req, pk="1")

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_svc.block_user.assert_called_once()

    def test_patch_with_valid_action_reestablecer(self, rf, mock_auth_admin):
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
            view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
            resp = view(req, pk="1")

        assert resp.status_code == 200
        assert resp.data["success"] is True

    def test_patch_with_invalid_action_returns_400(self, rf, mock_auth_admin):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"accion": "accion_inexistente"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
        resp = view(req, pk="1")

        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert "inválida" in resp.data["message"]

    def test_patch_without_action_or_rol_returns_400(self, rf, mock_auth_admin):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=json.dumps({"campo_irrelevante": True}),
            content_type="application/json",
        )
        req.session = MagicMock()

        view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
        resp = view(req, pk="1")

        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert "no especificada" in resp.data["message"]

    def test_patch_with_nuevoRol_calls_change_role(self, rf, mock_auth_admin):
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
            view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
            resp = view(req, pk="1")

        assert resp.status_code == 200
        mock_svc.change_role.assert_called_once()

    def test_patch_accion_takes_precedence_over_rol(self, rf, mock_auth_admin):
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
            view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
            resp = view(req, pk="1")

        assert resp.status_code == 200
        mock_svc.block_user.assert_called_once()
        mock_svc.change_role.assert_not_called()

    def test_patch_empty_body_returns_400(self, rf, mock_auth_admin):
        req = rf.patch(
            "/api/admin/usuarios/1",
            data=b"",
            content_type="application/json",
        )
        req.session = MagicMock()

        view = AdminUsuarioViewSet.as_view({"patch": "partial_update"})
        resp = view(req, pk="1")

        assert resp.status_code == 400


# ── BUG 3: AdminNotificacionView.delete — orden de require_role ────────────


class TestAdminNotificacionDelete:
    def test_delete_requires_auth(self, rf):
        req = rf.delete("/api/admin/notificaciones/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = AdminNotificacionAPIView.as_view()
            resp = view(req, id_notificacion=1)

        assert resp.status_code == 403

    def test_delete_without_id_returns_400(self, rf, mock_auth_admin):
        req = rf.delete("/api/admin/notificaciones/")
        req.session = MagicMock()

        view = AdminNotificacionAPIView.as_view()
        resp = view(req, id_notificacion=None)

        assert resp.status_code == 400
        assert "Falta id" in resp.data["message"]


# ── BUG FIX: AdminChatbotConfigView.get — tuple unpacking ─────────────────


class TestAdminChatbotConfigGet:
    def test_returns_flat_config_object(self, rf, mock_auth_admin):
        req = rf.get("/api/admin/chatbot-config")
        req.session = MagicMock()

        with patch("apps.chatbot.services.ChatbotConfigService") as MockCls:
            mock_svc = MagicMock()
            MockCls.return_value = mock_svc
            mock_svc.get_config.return_value = (
                {
                    "success": True,
                    "config": {
                        "system_prompt": "Test prompt",
                        "tone": "amigable",
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500,
                        "max_tokens_user": 1000,
                        "daily_message_limit": 20,
                    },
                },
                200,
            )
            view = AdminChatbotConfigViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        assert isinstance(resp.data["config"], dict)
        assert resp.data["config"]["system_prompt"] == "Test prompt"
        assert resp.data["config"]["temperature"] == 0.7

    def test_config_is_not_array(self, rf, mock_auth_admin):
        req = rf.get("/api/admin/chatbot-config")
        req.session = MagicMock()

        with patch("apps.chatbot.services.ChatbotConfigService") as MockCls:
            mock_svc = MagicMock()
            MockCls.return_value = mock_svc
            mock_svc.get_config.return_value = (
                {"success": True, "config": {"system_prompt": "", "tone": ""}},
                200,
            )
            view = AdminChatbotConfigViewSet.as_view({"get": "list"})
            resp = view(req)

        assert not isinstance(resp.data["config"], list)


# ── BUG FIX: AdminChatbotPalabrasView.get — tuple + aggregation ───────────


class TestAdminChatbotPalabrasGet:
    def test_returns_aggregated_palabras(self, rf, mock_auth_admin):
        req = rf.get("/api/admin/chatbot-config/palabras-detectadas")
        req.session = MagicMock()

        with patch("apps.chatbot.services.ChatbotConfigService") as MockCls:
            mock_svc = MagicMock()
            MockCls.return_value = mock_svc
            mock_svc.get_historial_palabras_riesgo.return_value = (
                {
                    "success": True,
                    "palabras": [
                        {
                            "palabra": "suicidio",
                            "nivel": "Alto",
                            "count": 3,
                            "pacientes": ["Juan", "Maria"],
                        },
                    ],
                },
                200,
            )
            view = AdminChatbotPalabrasAPIView.as_view()
            resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        assert isinstance(resp.data["palabras"], list)
        assert resp.data["palabras"][0]["palabra"] == "suicidio"
        assert resp.data["palabras"][0]["count"] == 3
        assert "Juan" in resp.data["palabras"][0]["pacientes"]

    def test_palabras_not_raw_tuple(self, rf, mock_auth_admin):
        req = rf.get("/api/admin/chatbot-config/palabras-detectadas")
        req.session = MagicMock()

        with patch("apps.chatbot.services.ChatbotConfigService") as MockCls:
            mock_svc = MagicMock()
            MockCls.return_value = mock_svc
            mock_svc.get_historial_palabras_riesgo.return_value = (
                {"success": True, "palabras": []},
                200,
            )
            view = AdminChatbotPalabrasAPIView.as_view()
            resp = view(req)

        assert "palabras" in resp.data
        assert isinstance(resp.data["palabras"], list)


# ── ChatbotConfigService.get_historial_palabras_riesgo aggregation ────────


class TestChatbotConfigServiceAggregation:
    def test_aggregates_words_from_multiple_patients(self):
        from apps.chatbot.services import ChatbotConfigService

        svc = ChatbotConfigService()
        svc.repo = MagicMock()
        svc.repo.get_historial_palabras_riesgo.return_value = [
            {"nombre": "Juan", "palabrasRiesgoDetectadas": "muerte,suicidio", "nivelEmocionalDetectado": "Alto"},
            {"nombre": "Maria", "palabrasRiesgoDetectadas": "muerte", "nivelEmocionalDetectado": "Alto"},
        ]

        payload, status = svc.get_historial_palabras_riesgo()
        assert status == 200
        assert payload["success"] is True
        palabras = payload["palabras"]
        assert len(palabras) == 2

        muerte = next(p for p in palabras if p["palabra"] == "muerte")
        assert muerte["count"] == 2
        assert "Juan" in muerte["pacientes"]
        assert "Maria" in muerte["pacientes"]

    def test_empty_rows_returns_empty_list(self):
        from apps.chatbot.services import ChatbotConfigService

        svc = ChatbotConfigService()
        svc.repo = MagicMock()
        svc.repo.get_historial_palabras_riesgo.return_value = []

        payload, status = svc.get_historial_palabras_riesgo()
        assert status == 200
        assert payload["palabras"] == []
