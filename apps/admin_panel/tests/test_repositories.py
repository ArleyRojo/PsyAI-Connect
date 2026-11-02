import pytest
from unittest.mock import patch, MagicMock

from apps.admin_panel.repositories import AdminRepository
from apps.authentication.models import Register
from apps.chatbot.models import ConversacionesChatbot


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


@pytest.mark.django_db
def test_chatbot_historial_rows_uses_patient_relation():
    patient = Register.objects.create_user(
        email="historial@test.com",
        nombre="Paciente Historial",
        password="TestPass123",
        rol="paciente",
    )
    ConversacionesChatbot.objects.create(
        idPaciente=patient,
        mensajeUsuario="Necesito apoyo",
        respuestaChatbot="Estoy aquí para escucharte",
        nivelEmocionalDetectado="Medio",
    )

    rows = AdminRepository().get_chatbot_historial_rows()

    assert rows == [
        {
            "nombre": "Paciente Historial",
            "idPaciente": patient.idUsuario,
            "mensajeUsuario": "Necesito apoyo",
            "respuestaChatbot": "Estoy aquí para escucharte",
            "nivelEmocionalDetectado": "Medio",
            "fecha": rows[0]["fecha"],
        }
    ]


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


# ── Notificaciones admin por canal (paciente) ──────────────────────────────


@pytest.mark.django_db
class TestAdminNotificationPerCanal:
    """_send_admin_notification_emails respeta canalNotificacion de pacientes."""

    def _make_user(self, email, rol, nombre):
        return Register.objects.create_user(
            email=email, password="x", rol=rol, nombre=nombre,
        )

    def _make_patient(self, email, nombre, **perfil_kwargs):
        user = self._make_user(email, "paciente", nombre)
        defaults = dict(
            canalNotificacion="email",
            whatsappConsentimiento=False,
            numeroTelefonico=None,
            recibirNotificacionesAdmin=True,
        )
        defaults.update(perfil_kwargs)
        from apps.patients.models import PerfilPaciente
        PerfilPaciente.objects.create(idPaciente=user, **defaults)
        return user

    @patch("apps.core.notifier.notificar_paciente")
    def test_paciente_canal_email_envia_por_notificar_paciente(self, mock_notify):
        """Canal email: notificar_paciente se llama con plantilla_email."""
        mock_notify.return_value = True
        repo = AdminRepository()
        user = self._make_patient("pac_email@test.com", "Pac Email")
        enviados, fallidos, omitidos, error = repo._send_admin_notification_emails(
            notificacion_id=1, destinatario="pacientes", email_individual=None,
            titulo="Aviso admin", mensaje="Mensaje de prueba", tipo="info",
        )
        mock_notify.assert_called_once()
        _, args, kwargs = mock_notify.mock_calls[0]
        assert args[0] == user
        assert args[3] == "notificacion_admin"
        assert kwargs["plantilla_email"] == "emails/notificacion_admin.html"
        assert "params_email" in kwargs
        assert enviados == 1
        assert fallidos == 0
        assert omitidos == 0

    @patch("apps.core.notifier.notificar_paciente")
    def test_paciente_canal_whatsapp_no_correo_directo(self, mock_notify):
        """Canal whatsapp: notificar_paciente se llama, no correo directo."""
        mock_notify.return_value = True
        repo = AdminRepository()
        user = self._make_patient(
            "pac_wa@test.com", "Pac WA",
            canalNotificacion="whatsapp",
            whatsappConsentimiento=True,
            numeroTelefonico="+573001234567",
        )
        enviados, fallidos, omitidos, error = repo._send_admin_notification_emails(
            notificacion_id=1, destinatario="pacientes", email_individual=None,
            titulo="Aviso admin", mensaje="Mensaje de prueba", tipo="info",
        )
        mock_notify.assert_called_once()
        assert enviados == 1
        assert omitidos == 0

    @patch("apps.core.notifier.notificar_paciente")
    def test_paciente_canal_ambos_notificar_paciente(self, mock_notify):
        """Canal ambos: notificar_paciente se llama (cubre email + whatsapp)."""
        mock_notify.return_value = True
        repo = AdminRepository()
        user = self._make_patient(
            "pac_both@test.com", "Pac Ambos",
            canalNotificacion="ambos",
            whatsappConsentimiento=True,
            numeroTelefonico="+573001234567",
        )
        enviados, fallidos, omitidos, error = repo._send_admin_notification_emails(
            notificacion_id=1, destinatario="pacientes", email_individual=None,
            titulo="Aviso admin", mensaje="Mensaje de prueba", tipo="info",
        )
        mock_notify.assert_called_once()
        assert enviados == 1
        assert omitidos == 0

    @patch("apps.core.notifier.notificar_paciente")
    def test_paciente_canal_ninguno_omitido_no_fallido(self, mock_notify):
        """Canal ninguno: notificar_paciente se llama pero retorna False → omitido."""
        mock_notify.return_value = False
        repo = AdminRepository()
        user = self._make_patient(
            "pac_none@test.com", "Pac Ninguno",
            canalNotificacion="ninguno",
        )
        enviados, fallidos, omitidos, error = repo._send_admin_notification_emails(
            notificacion_id=1, destinatario="pacientes", email_individual=None,
            titulo="Aviso admin", mensaje="Mensaje de prueba", tipo="info",
        )
        mock_notify.assert_called_once()
        assert enviados == 0
        assert fallidos == 0  # ninguno no es fallido
        assert omitidos == 1  # contador de omitidos

    @patch("apps.core.notifier.notificar_paciente")
    def test_profesional_envia_correo_directo_no_notificar_paciente(self, mock_notify):
        """Profesional: correo directo, no notificar_paciente."""
        repo = AdminRepository()
        user = self._make_user("prof@test.com", "profesional", "Prof Test")
        enviados, fallidos, omitidos, error = repo._send_admin_notification_emails(
            notificacion_id=1, destinatario="profesionales", email_individual=None,
            titulo="Aviso admin", mensaje="Mensaje de prueba", tipo="alerta",
        )
        mock_notify.assert_not_called()
        assert enviados == 1
        assert fallidos == 0
        assert omitidos == 0
        assert error is None


@pytest.mark.django_db
class TestAdminNotificationMixedChannels:
    """Notificación masiva con pacientes de canales mezclados."""

    def _make_patient(self, email, nombre, **perfil_kwargs):
        user = Register.objects.create_user(
            email=email, password="x", rol="paciente", nombre=nombre,
        )
        defaults = dict(
            canalNotificacion="email",
            whatsappConsentimiento=False,
            numeroTelefonico=None,
            recibirNotificacionesAdmin=True,
        )
        defaults.update(perfil_kwargs)
        from apps.patients.models import PerfilPaciente
        PerfilPaciente.objects.create(idPaciente=user, **defaults)
        return user

    @patch("apps.core.notifier.notificar_paciente")
    def test_mezcla_canales_cada_paciente_recibe_lo_que_eligio(self, mock_notify):
        """Pacientes con distintos canales: cada uno se enruta por notificar_paciente."""
        mock_notify.return_value = True
        repo = AdminRepository()

        p_email = self._make_patient("a@test.com", "A", canalNotificacion="email")
        p_wa = self._make_patient(
            "b@test.com", "B",
            canalNotificacion="whatsapp",
            whatsappConsentimiento=True,
            numeroTelefonico="+573001234567",
        )
        p_ambos = self._make_patient(
            "c@test.com", "C",
            canalNotificacion="ambos",
            whatsappConsentimiento=True,
            numeroTelefonico="+573001234567",
        )
        p_none = self._make_patient(
            "d@test.com", "D",
            canalNotificacion="ninguno",
        )
        # Profesional (correo directo)
        prof = Register.objects.create_user(
            email="prof@test.com", password="x", rol="profesional", nombre="Prof",
        )

        enviados, fallidos, omitidos, error = repo._send_admin_notification_emails(
            notificacion_id=1, destinatario="todos", email_individual=None,
            titulo="Mezcla", mensaje="Mensaje", tipo="info",
        )

        # notificar_paciente llamado para los 4 pacientes (incluido ninguno)
        assert mock_notify.call_count == 4
        # El profesional recibe correo directo → 1 enviado adicional
        assert enviados >= 1
