import json
import pytest
from unittest.mock import patch, MagicMock
from django.core import mail
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestAdminNotificationAPI:
    """Tests for POST /api/admin/notificaciones"""

    def _login_admin(self, client, django_user_model):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        from apps.authentication.models import Register
        hashed = SecurityHelper.hash_password("AdminPass123")
        # Crear admin directamente para evitar problemas de rol en login
        admin = Register.objects.create(
            nombre="Admin Test",
            email="admin_notif@test.com",
            contrasena=hashed,
            rol="admin",
            activo=True,
            estadoCuenta="Activa"
        )
        # Login como admin
        client.post(
            "/api/login",
            data=json.dumps({"email": "admin_notif@test.com", "password": "AdminPass123", "rol": "admin"}),
            content_type="application/json",
        )
        return admin

    def _make_patient(self, django_user_model, email, nombre="Paciente Test"):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        from apps.patients.models import PerfilPaciente
        from apps.authentication.models import Register
        hashed = SecurityHelper.hash_password("TestPass123")
        user = Register.objects.create(
            nombre=nombre,
            email=email,
            contrasena=hashed,
            rol="paciente",
            activo=True,
            estadoCuenta="Activa"
        )
        PerfilPaciente.objects.create(idPaciente=user)
        return user

    def _make_professional(self, django_user_model, email, nombre="Profesional Test"):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        from apps.professionals.models import PerfilProfesional
        from apps.authentication.models import Register
        hashed = SecurityHelper.hash_password("TestPass123")
        user = Register.objects.create(
            nombre=nombre,
            email=email,
            contrasena=hashed,
            rol="profesional",
            activo=True,
            estadoCuenta="Activa"
        )
        PerfilProfesional.objects.create(idProfesional=user)
        return user

    def test_immediate_individual_sends_one_email_with_correct_subject_and_content(self, client, django_user_model):
        """POST admin inmediato a individual → 1 correo, asunto 'PsyAI Connect — {titulo}',
        HTML con el mensaje del admin y sin 'Prediagnostico' ni 'Resumen'."""
        self._login_admin(client, django_user_model)
        
        payload = {
            "titulo": "Mantenimiento programado",
            "mensaje": "El sistema estará en mantenimiento el domingo de 2:00 a 4:00 AM.",
            "tipo": "sistema",
            "destinatario": "individual",
            "envio": "inmediato",
            "email_individual": "usuario@ejemplo.com",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 200, f"Response: {response.json()}"
        data = response.json()
        assert data["success"] is True
        assert "idNotificacion" in data
        
        # Verificar que se envió 1 email
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        
        # Asunto correcto
        assert email.subject == "PsyAI Connect \u2014 Mantenimiento programado"
        
        # HTML contiene el mensaje del admin
        html_body = email.alternatives[0][0]
        assert "Mantenimiento programado" in html_body
        assert "El sistema estar\u00e1 en mantenimiento" in html_body
        
        # NO contiene contenido de prediagnóstico
        assert "Prediagnostico" not in html_body
        assert "Resumen clinico" not in html_body
        assert "Apoyo orientativo generado por IA" not in html_body
        assert "Nivel de riesgo" not in html_body
        assert "Ver prediagnostico completo" not in html_body
        
        # Contiene botón "Ir a PsyAI Connect"
        assert "Ir a PsyAI Connect" in html_body
        
        # Saludo con nombre (fallback a parte local del email)
        assert "Hola <strong>Usuario</strong>" in html_body or "Hola <strong>usuario</strong>" in html_body
        
        # Badge de tipo "Sistema"
        assert "Sistema" in html_body

    def test_immediate_todos_sends_to_patients_and_professionals_not_admins(self, client, django_user_model):
        """POST admin inmediato a 'todos' → envía a pacientes y profesionales, NO a admins."""
        self._login_admin(client, django_user_model)
        
        # Crear usuarios de prueba
        self._make_patient(django_user_model, "paciente1@test.com", "Paciente Uno")
        self._make_patient(django_user_model, "paciente2@test.com", "Paciente Dos")
        self._make_professional(django_user_model, "prof1@test.com", "Prof Uno")
        # Crear otro admin (no debe recibir)
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        hashed = SecurityHelper.hash_password("AdminPass123")
        AuthRepository().create_user("Otro Admin", "admin2@test.com", hashed, "admin")
        
        payload = {
            "titulo": "Anuncio general",
            "mensaje": "Nueva funcionalidad disponible.",
            "tipo": "info",
            "destinatario": "todos",
            "envio": "inmediato",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Debe haber 3 emails (2 pacientes + 1 profesional), NO el admin
        assert len(mail.outbox) == 3
        emails = [e.to[0] for e in mail.outbox]
        assert "paciente1@test.com" in emails
        assert "paciente2@test.com" in emails
        assert "prof1@test.com" in emails
        assert "admin2@test.com" not in emails
        assert "admin_notif@test.com" not in emails  # el admin que envía tampoco

    def test_immediate_pacientes_excludes_prefNotificaciones_desactivadas(self, client, django_user_model):
        """Pacientes con prefNotificaciones='Desactivadas' no reciben correo."""
        self._login_admin(client, django_user_model)
        
        p1 = self._make_patient(django_user_model, "paciente_on@test.com", "Paciente On")
        p2 = self._make_patient(django_user_model, "paciente_off@test.com", "Paciente Off")
        
        # Desactivar notificaciones para p2
        from apps.patients.models import PerfilPaciente
        perfil = PerfilPaciente.objects.get(idPaciente=p2)
        perfil.prefNotificaciones = "Desactivadas"
        perfil.save()
        
        payload = {
            "titulo": "Solo para activos",
            "mensaje": "Esto no debe llegar a p2",
            "tipo": "info",
            "destinatario": "pacientes",
            "envio": "inmediato",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to[0] == "paciente_on@test.com"

    def test_immediate_profesionales_only_sends_to_professionals(self, client, django_user_model):
        """POST admin inmediato a 'profesionales' → solo profesionales."""
        self._login_admin(client, django_user_model)
        
        self._make_patient(django_user_model, "paciente@test.com", "Paciente")
        self._make_professional(django_user_model, "prof@test.com", "Profesional")
        
        payload = {
            "titulo": "Solo pros",
            "mensaje": "Mensaje para profesionales",
            "tipo": "alerta",
            "destinatario": "profesionales",
            "envio": "inmediato",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to[0] == "prof@test.com"
        
        # Verificar badge de tipo "Alerta" en HTML
        html_body = mail.outbox[0].alternatives[0][0]
        assert "Alerta" in html_body

    def test_scheduled_returns_200_zero_emails_status_pendiente(self, client, django_user_model):
        """POST programado → 0 correos, estado 'pendiente'."""
        self._login_admin(client, django_user_model)
        
        future = timezone.now() + timedelta(hours=1)
        payload = {
            "titulo": "Programada para después",
            "mensaje": "Esta se enviará luego",
            "tipo": "recordatorio",
            "destinatario": "todos",
            "envio": "programado",
            "fecha_programada": future.strftime("%Y-%m-%dT%H:%M"),
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "programada" in data["message"].lower()
        
        # Cero emails enviados
        assert len(mail.outbox) == 0
        
        # Verificar en BD que quedó pendiente
        from apps.scheduling.models import Notificaciones
        notif = Notificaciones.objects.get(idNotificacion=data["idNotificacion"])
        assert notif.estado == "pendiente"
        assert notif.canal == "email"
        assert notif.enviado_por == "Admin"

    def test_no_recipients_returns_fallido_success_false(self, client, django_user_model):
        """Sin destinatarios → estado 'fallido', respuesta success: false."""
        self._login_admin(client, django_user_model)
        
        # No crear ningún paciente/profesional activo
        payload = {
            "titulo": "Sin destinatarios",
            "mensaje": "Nadie recibirá esto",
            "tipo": "info",
            "destinatario": "pacientes",
            "envio": "inmediato",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        # Debe fallar (502) porque no hay destinatarios
        assert response.status_code == 502
        data = response.json()
        assert data["success"] is False
        assert "destinatario" in data["message"].lower() or "destinatarios" in data["message"].lower()
        
        # Verificar en BD que quedó fallido
        from apps.scheduling.models import Notificaciones
        notif = Notificaciones.objects.get(idNotificacion=data["idNotificacion"])
        assert notif.estado == "fallido"
        assert notif.errorDetalle is not None

    def test_invalid_email_individual_returns_400_no_notification_created(self, client, django_user_model):
        """Email individual inválido → 400 y no se crea la notificación."""
        self._login_admin(client, django_user_model)
        
        payload = {
            "titulo": "Test",
            "mensaje": "Test",
            "tipo": "info",
            "destinatario": "individual",
            "envio": "inmediato",
            "email_individual": "email-invalido",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "inválido" in data["message"].lower() or "invalid" in data["message"].lower()
        
        # No se creó notificación en BD
        from apps.scheduling.models import Notificaciones
        assert Notificaciones.objects.count() == 0

    def test_missing_required_fields_returns_400(self, client, django_user_model):
        """Campos obligatorios faltantes → 400."""
        self._login_admin(client, django_user_model)
        
        # Sin título
        payload = {
            "mensaje": "Test",
            "tipo": "info",
            "destinatario": "todos",
            "envio": "inmediato",
        }
        
        response = client.post(
            "/api/admin/notificaciones",
            data=json.dumps(payload),
            content_type="application/json",
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "obligatorio" in data["message"].lower() or "requerido" in data["message"].lower()


@pytest.mark.django_db
class TestScheduledNotificationsCommand:
    """Tests for management command enviar_notificaciones_programadas"""

    def _login_admin(self, client, django_user_model):
        from apps.authentication.models import Register
        from apps.authentication.security import SecurityHelper
        hashed = SecurityHelper.hash_password("AdminPass123")
        Register.objects.create(
            nombre="Admin Test",
            email="admin_cmd@test.com",
            contrasena=hashed,
            rol="admin",
            activo=True,
            estadoCuenta="Activa"
        )
        client.post(
            "/api/login",
            data=json.dumps({"email": "admin_cmd@test.com", "password": "AdminPass123", "rol": "admin"}),
            content_type="application/json",
        )

    def _make_patient(self, django_user_model, email, nombre="Paciente Test"):
        from apps.authentication.models import Register
        from apps.authentication.security import SecurityHelper
        from apps.patients.models import PerfilPaciente
        hashed = SecurityHelper.hash_password("TestPass123")
        user = Register.objects.create(
            nombre=nombre,
            email=email,
            contrasena=hashed,
            rol="paciente",
            activo=True,
            estadoCuenta="Activa"
        )
        PerfilPaciente.objects.create(idPaciente=user)
        return user

    def test_command_sends_pending_notifications(self, client, django_user_model):
        """Comando envía notificaciones pendientes con fecha_programada <= now."""
        from django.core.management import call_command
        from apps.scheduling.models import Notificaciones
        from django.utils import timezone
        
        self._login_admin(client, django_user_model)
        self._make_patient(django_user_model, "paciente_cmd@test.com", "Paciente Cmd")
        
        # Crear notificación programada en el pasado directamente en BD
        past = timezone.now() - timedelta(minutes=10)
        notif = Notificaciones.objects.create(
            titulo="Programada antigua",
            mensaje="Esta ya debería haberse enviado",
            tipo="info",
            destinatario="pacientes",
            enviado_por="Admin",
            estado="pendiente",
            canal="email",
            fecha_programada=past,
        )
        
        # Ejecutar comando
        call_command("enviar_notificaciones_programadas")
        
        # Verificar que se envió
        notif.refresh_from_db()
        assert notif.estado == "enviado"
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "PsyAI Connect \u2014 Programada antigua"

    def test_command_ignores_future_notifications(self, client, django_user_model):
        """Comando ignora notificaciones con fecha_programada > now."""
        from django.core.management import call_command
        from apps.scheduling.models import Notificaciones
        from django.utils import timezone
        
        self._login_admin(client, django_user_model)
        self._make_patient(django_user_model, "paciente_future@test.com", "Paciente Future")
        
        future = timezone.now() + timedelta(hours=1)
        notif = Notificaciones.objects.create(
            titulo="Programada futura",
            mensaje="Esta NO debe enviarse aún",
            tipo="info",
            destinatario="pacientes",
            enviado_por="Admin",
            estado="pendiente",
            canal="email",
            fecha_programada=future,
        )
        
        call_command("enviar_notificaciones_programadas")
        
        # No debe haber enviado nada
        notif.refresh_from_db()
        assert notif.estado == "pendiente"
        assert len(mail.outbox) == 0

    def test_command_only_sends_admin_notifications(self, client, django_user_model):
        """Comando solo envía notificaciones con enviado_por='Admin'."""
        from django.core.management import call_command
        from apps.scheduling.models import Notificaciones
        from django.utils import timezone
        
        self._login_admin(client, django_user_model)
        self._make_patient(django_user_model, "paciente_admin@test.com", "Paciente Admin")
        
        past = timezone.now() - timedelta(minutes=10)
        # Notificación de admin
        Notificaciones.objects.create(
            titulo="De Admin",
            mensaje="Debe enviarse",
            tipo="info",
            destinatario="pacientes",
            enviado_por="Admin",
            estado="pendiente",
            canal="email",
            fecha_programada=past,
        )
        # Notificación de sistema (no admin)
        Notificaciones.objects.create(
            titulo="De Sistema",
            mensaje="No debe enviarse",
            tipo="info",
            destinatario="pacientes",
            enviado_por="Sistema",
            estado="pendiente",
            canal="email",
            fecha_programada=past,
        )
        
        call_command("enviar_notificaciones_programadas")
        
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "PsyAI Connect \u2014 De Admin"


@pytest.mark.django_db
class TestPrediagnosticoEmailStillWorks:
    """Verificar que generar_prediagnostico sigue enviando su correo a los profesionales."""

    def test_generar_prediagnostico_sends_email_to_professionals(self, django_user_model):
        """generar_prediagnostico sigue enviando su correo a los profesionales."""
        from apps.chatbot.services import ChatbotService
        from apps.chatbot.repositories import ChatRepository
        from apps.authentication.models import Register
        from apps.authentication.security import SecurityHelper
        from apps.professionals.models import PerfilProfesional
        import json
        
        # Crear paciente y profesional
        hashed = SecurityHelper.hash_password("TestPass123")
        patient = Register.objects.create(
            nombre="Paciente Prediag",
            email="patient_prediag@test.com",
            contrasena=hashed,
            rol="paciente",
            activo=True,
            estadoCuenta="Activa"
        )
        prof = Register.objects.create(
            nombre="Prof Prediag",
            email="prof_prediag@test.com",
            contrasena=hashed,
            rol="profesional",
            activo=True,
            estadoCuenta="Activa"
        )
        PerfilProfesional.objects.create(idProfesional=prof)
        
        svc = ChatbotService()
        
        # Mock history y Gemini response
        fake_history = [
            {"tipo": "usuario", "mensaje": "Me siento ansioso", "nivel_emocional": "Moderado"},
            {"tipo": "bot", "mensaje": "Te escucho", "nivel_emocional": None},
        ]
        gemini_response = json.dumps({
            "resumen_paciente": "Hoy compartiste ansiedad.",
            "resumen_profesional": "Patrones de ansiedad leve.",
            "posibles_areas": ["Ansiedad"],
            "recomendaciones_paciente": ["Respirar", "Hablar con profesional"],
            "nivel_riesgo": "moderado",
            "requiere_atencion_urgente": False,
        })
        
        with (
            patch.object(svc.chat_repo, "get_history", return_value=fake_history),
            patch.object(svc, "_get_api_keys", return_value=["fake_key"]),
            patch.object(svc, "_call_gemini_json", return_value=gemini_response),
            patch.object(svc.chat_repo, "get_professional_emails", return_value=[("prof_prediag@test.com", "Prof Prediag")]),
            patch.object(svc.appointment_repo, "create_notification"),
        ):
            result, status = svc.generar_prediagnostico(patient_id=patient.pk)
        
        assert status == 201
        assert result["success"] is True
        
        # Verificar que se envió email de prediagnóstico (usa template prediagnostico.html)
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to[0] == "prof_prediag@test.com"
        assert "Nuevo prediagnóstico disponible" in email.subject
        
        html_body = email.alternatives[0][0]
        # Debe usar template prediagnostico.html
        assert "Nuevo Prediagnostico Disponible" in html_body
        assert "Apoyo orientativo generado por IA" in html_body
        assert "Nivel de riesgo" in html_body
        # Debe tener saludo con nombre del profesional
        assert "Hola <strong>Prof Prediag</strong>" in html_body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])