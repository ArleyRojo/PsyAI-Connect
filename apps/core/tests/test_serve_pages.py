from unittest.mock import MagicMock

import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import override_settings

from apps.core.views import serve_pages


def _make_request(rf, path, session_data=None):
    request = rf.get(path)
    mock_session = MagicMock()
    if session_data:
        mock_session.get = lambda key, default=None: session_data.get(key, default)
        mock_session.__contains__ = lambda self, key: key in session_data
    else:
        mock_session.get = lambda key, default=None: default
        mock_session.__contains__ = lambda self, key: False
    request.session = mock_session
    return request


# ── admin.dashboard.html ─────────────────────────────────────────────────


class TestAdminDashboardAccess:
    def test_anonymous_redirects_to_login(self, rf):
        request = _make_request(rf, "/admin.dashboard.html")
        resp = serve_pages(request, "admin.dashboard.html")
        assert resp.status_code == 302
        assert resp.url == "/login.html"

    def test_wrong_role_raises_403(self, rf):
        request = _make_request(rf, "/admin.dashboard.html", {"rol": "paciente"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "admin.dashboard.html")

    def test_correct_role_returns_200(self, rf):
        request = _make_request(rf, "/admin.dashboard.html", {"rol": "admin"})
        resp = serve_pages(request, "admin.dashboard.html")
        assert resp.status_code == 200


class TestAdminAsideAccess:
    def test_anonymous_redirects_to_login(self, rf):
        request = _make_request(rf, "/aside-admin/users.html")
        resp = serve_pages(request, "aside-admin/users.html")
        assert resp.status_code == 302
        assert resp.url == "/login.html"

    def test_wrong_role_raises_403(self, rf):
        request = _make_request(rf, "/aside-admin/users.html", {"rol": "profesional"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "aside-admin/users.html")

    def test_correct_role_returns_200(self, rf):
        request = _make_request(rf, "/aside-admin/users.html", {"rol": "admin"})
        resp = serve_pages(request, "aside-admin/users.html")
        assert resp.status_code == 200


# ── patient.dashboard.html ───────────────────────────────────────────────


class TestPatientDashboardAccess:
    def test_anonymous_redirects_to_login(self, rf):
        request = _make_request(rf, "/patient.dashboard.html")
        resp = serve_pages(request, "patient.dashboard.html")
        assert resp.status_code == 302
        assert resp.url == "/login.html"

    def test_wrong_role_raises_403(self, rf):
        request = _make_request(rf, "/patient.dashboard.html", {"rol": "admin"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "patient.dashboard.html")

    def test_correct_role_returns_200(self, rf):
        request = _make_request(rf, "/patient.dashboard.html", {"rol": "paciente"})
        resp = serve_pages(request, "patient.dashboard.html")
        assert resp.status_code == 200


class TestPatientAsideAccess:
    def test_anonymous_redirects_to_login(self, rf):
        request = _make_request(rf, "/aside-patient/chatbot.html")
        resp = serve_pages(request, "aside-patient/chatbot.html")
        assert resp.status_code == 302
        assert resp.url == "/login.html"

    def test_wrong_role_raises_403(self, rf):
        request = _make_request(rf, "/aside-patient/chatbot.html", {"rol": "profesional"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "aside-patient/chatbot.html")

    def test_correct_role_returns_200(self, rf):
        request = _make_request(rf, "/aside-patient/chatbot.html", {"rol": "paciente"})
        resp = serve_pages(request, "aside-patient/chatbot.html")
        assert resp.status_code == 200


# ── professional.dashboard.html ──────────────────────────────────────────


class TestProfessionalDashboardAccess:
    def test_anonymous_redirects_to_login(self, rf):
        request = _make_request(rf, "/professional.dashboard.html")
        resp = serve_pages(request, "professional.dashboard.html")
        assert resp.status_code == 302
        assert resp.url == "/login.html"

    def test_wrong_role_raises_403(self, rf):
        request = _make_request(rf, "/professional.dashboard.html", {"rol": "paciente"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "professional.dashboard.html")

    def test_correct_role_returns_200(self, rf):
        request = _make_request(rf, "/professional.dashboard.html", {"rol": "profesional"})
        resp = serve_pages(request, "professional.dashboard.html")
        assert resp.status_code == 200


class TestProfessionalAsideAccess:
    def test_anonymous_redirects_to_login(self, rf):
        request = _make_request(rf, "/aside-professional/patients.html")
        resp = serve_pages(request, "aside-professional/patients.html")
        assert resp.status_code == 302
        assert resp.url == "/login.html"

    def test_wrong_role_raises_403(self, rf):
        request = _make_request(rf, "/aside-professional/patients.html", {"rol": "admin"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "aside-professional/patients.html")

    def test_correct_role_returns_200(self, rf):
        request = _make_request(rf, "/aside-professional/patients.html", {"rol": "profesional"})
        resp = serve_pages(request, "aside-professional/patients.html")
        assert resp.status_code == 200


# ── unaffected pages (regression check) ──────────────────────────────────


class TestUnaffectedPages:
    def test_index_still_works(self, rf):
        request = _make_request(rf, "/index.html")
        resp = serve_pages(request, "index.html")
        assert resp.status_code == 200

    def test_landing_assets_are_served(self, rf):
        request = _make_request(rf, "/js/core/shared/theme-inline.js")
        resp = serve_pages(request, "js/core/shared/theme-inline.js")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/javascript")

    def test_login_still_works(self, rf):
        request = _make_request(rf, "/login.html")
        resp = serve_pages(request, "login.html")
        assert resp.status_code == 200

    @override_settings(DEBUG=True, ALLOW_PAGE_PREVIEW_WITHOUT_SESSION=True)
    def test_professional_patient_page_is_available_in_preview_mode(self, rf):
        request = _make_request(rf, "/aside-professional/patients.html")
        resp = serve_pages(request, "aside-professional/patients.html")
        assert resp.status_code == 200

    @override_settings(DEBUG=True, ALLOW_PAGE_PREVIEW_WITHOUT_SESSION=False)
    def test_debug_alone_does_not_skip_role_check(self, rf):
        request = _make_request(rf, "/aside-professional/patients.html", {"rol": "paciente"})
        with pytest.raises(PermissionDenied):
            serve_pages(request, "aside-professional/patients.html")

    @override_settings(DEBUG=False, ALLOW_PAGE_PREVIEW_WITHOUT_SESSION=True)
    def test_preview_flag_is_ignored_in_production(self, rf):
        request = _make_request(rf, "/aside-admin/users.html")
        resp = serve_pages(request, "aside-admin/users.html")
        assert resp.status_code == 302

    def test_nonexistent_page_raises_404(self, rf):
        request = _make_request(rf, "/nonexistent.page.html")
        with pytest.raises(Http404):
            serve_pages(request, "nonexistent.page.html")
