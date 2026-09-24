import json
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.test import APIRequestFactory
from rest_framework import status


class SessionRequestFactory(APIRequestFactory):
    def generic(self, *args, **kwargs):
        request = super().generic(*args, **kwargs)
        request.session = SessionStore()
        return request

from apps.chatbot.views import (
    ChatbotViewSet,
    ChatbotConfigViewSet,
    ChatContactoViewSet,
    ChatMensajeViewSet,
    ChatHistorialDeleteViewSet,
)
from apps.core.permissions import IsAuthenticatedDRF

PACIENTE_USER = {"idUsuario": 1, "rol": "paciente", "nombre": "Test"}

FACTORY = SessionRequestFactory()


def _auth_paciente(_self, request, view):
    request.user_id = 1
    request.user_role = "paciente"
    request.user_name = "Paciente Test"
    return True


@pytest.fixture
def mock_auth_paciente():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
        yield


# ── ChatbotViewSet ──────────────────────────────────────────────────────────


class TestChatbotViewSetPost:
    @patch("apps.chatbot.views.chatbot_service")
    def test_post_returns_200(self, mock_svc, mock_auth_paciente):
        mock_svc.build_response.return_value = ({"success": True, "respuesta": "Hola"}, 200)
        req = FACTORY.post("/chatbot", data=json.dumps({"mensaje": "Hola"}), content_type="application/json")
        view = ChatbotViewSet.as_view({"post": "create"})
        resp = view(req)
        assert resp.status_code == 200
        mock_svc.build_response.assert_called_once_with(1, "Hola")

    def test_post_no_auth(self):
        req = FACTORY.post("/chatbot", data=json.dumps({"mensaje": "Hola"}), content_type="application/json")
        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ChatbotViewSet.as_view({"post": "create"})
            resp = view(req)
        assert resp.status_code == 403


class TestChatbotViewSetGet:
    @patch("apps.chatbot.views.chatbot_service")
    def test_get_returns_history(self, mock_svc, mock_auth_paciente):
        mock_svc.get_history.return_value = ({"success": True, "historial": []}, 200)
        req = FACTORY.get("/chatbot")
        view = ChatbotViewSet.as_view({"get": "list"})
        resp = view(req)
        assert resp.status_code == 200
        mock_svc.get_history.assert_called_once_with(1)


class TestChatbotViewSetDelete:
    @patch("apps.chatbot.views.mensajes_service")
    def test_delete_calls_eliminar(self, mock_svc, mock_auth_paciente):
        req = FACTORY.delete("/chatbot")
        view = ChatbotViewSet.as_view({"delete": "destroy"})
        resp = view(req)
        assert resp.status_code == 200
        mock_svc.eliminar_historial_chatbot.assert_called_once_with(1)


# ── ChatbotConfigViewSet ────────────────────────────────────────────────────


class TestChatbotConfigViewSetGet:
    @patch("apps.chatbot.views.chatbot_service")
    @patch("apps.chatbot.views.chatbot_config_service")
    def test_get_returns_config(self, mock_svc, mock_chat_svc, mock_auth_paciente):
        mock_svc.get_config.return_value = (
            {"success": True, "config": {"max_tokens": 600, "max_tokens_user": 1000, "daily_message_limit": 20}},
            200,
        )
        mock_chat_svc.chat_repo.count_today_messages.return_value = 0
        req = FACTORY.get("/chatbot/config")
        view = ChatbotConfigViewSet.as_view({"get": "list"})
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["success"] is True
        assert "config" in resp.data


# ── ChatContactoViewSet ─────────────────────────────────────────────────────


class TestChatContactoViewSetGet:
    @patch("apps.chatbot.views.mensajes_service")
    @patch("apps.professionals.services.ProfessionalService")
    def test_get_returns_profesionales(self, MockProSvc, mock_msgs, mock_auth_paciente):
        MockProSvc.return_value.list_professionals.return_value = (
            {"profesionales": [{"idUsuario": 10}]},
            200,
        )
        mock_msgs.get_contactos_con_mensajes.return_value = []
        req = FACTORY.get("/chat/contactos")
        view = ChatContactoViewSet.as_view({"get": "list"})
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["success"] is True
        assert "profesionales" in resp.data


# ── ChatMensajeViewSet ──────────────────────────────────────────────────────


class TestChatMensajeViewSetGet:
    @patch("apps.chatbot.views.mensajes_service")
    def test_get_requires_receptor(self, mock_svc, mock_auth_paciente):
        req = FACTORY.get("/chat/mensajes")
        view = ChatMensajeViewSet.as_view({"get": "list"})
        resp = view(req)
        assert resp.status_code == 400

    @patch("apps.chatbot.views.mensajes_service")
    def test_get_returns_mensajes(self, mock_svc, mock_auth_paciente):
        mock_svc.get_mensajes.return_value = []
        req = FACTORY.get("/chat/mensajes?receptor=2")
        view = ChatMensajeViewSet.as_view({"get": "list"})
        resp = view(req)
        assert resp.status_code == 200


class TestChatMensajeViewSetPost:
    @patch("apps.chatbot.views.mensajes_service")
    def test_post_sends_message(self, mock_svc, mock_auth_paciente):
        mock_svc.enviar_mensaje.return_value = 99
        req = FACTORY.post("/chat/mensajes", data=json.dumps({"receptor": 2, "mensaje": "Hola"}), content_type="application/json")
        view = ChatMensajeViewSet.as_view({"post": "create"})
        resp = view(req)
        assert resp.status_code == 201
        mock_svc.enviar_mensaje.assert_called_once_with(1, 2, "Hola")

    def test_post_missing_fields(self, mock_auth_paciente):
        req = FACTORY.post("/chat/mensajes", data=json.dumps({"mensaje": ""}), content_type="application/json")
        view = ChatMensajeViewSet.as_view({"post": "create"})
        resp = view(req)
        assert resp.status_code == 400

    def test_post_long_message(self, mock_auth_paciente):
        req = FACTORY.post("/chat/mensajes", data=json.dumps({"receptor": 2, "mensaje": "x" * 2001}), content_type="application/json")
        view = ChatMensajeViewSet.as_view({"post": "create"})
        resp = view(req)
        assert resp.status_code == 400

    def test_post_no_auth(self):
        req = FACTORY.post("/chat/mensajes", data=json.dumps({"receptor": 2, "mensaje": "Hola"}), content_type="application/json")
        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ChatMensajeViewSet.as_view({"post": "create"})
            resp = view(req)
        assert resp.status_code == 403


# ── ChatHistorialDeleteViewSet ──────────────────────────────────────────────


class TestChatHistorialDeleteViewSet:
    @patch("apps.chatbot.views.mensajes_service")
    def test_delete_calls_eliminar(self, mock_svc, mock_auth_paciente):
        req = FACTORY.delete("/chat/historial")
        view = ChatHistorialDeleteViewSet.as_view({"delete": "destroy"})
        resp = view(req)
        assert resp.status_code == 200
        mock_svc.eliminar_historial_chatbot.assert_called_once_with(1)
