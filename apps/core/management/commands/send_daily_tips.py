from datetime import date

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from apps.core.models import NewsletterSubscriber


DAILY_TIPS = [
    {
        "title": "Respiracion 4-7-8",
        "body": (
            "Inhala por la nariz durante 4 segundos, sostén el aire 7 segundos "
            "y exhala lentamente por la boca durante 8 segundos. Repite 4 veces. "
            "Esta tecnica activa el sistema nervioso parasimpatico y reduce la ansiedad en minutos."
        ),
    },
    {
        "title": "Diario de gratitud",
        "body": (
            "Escribe 3 cosas por las que estes agradecido hoy. Pueden ser simples: "
            "un cafe caliente, una conversacion agradable, o el sol en tu cara. "
            "Estudios muestran que hacerlo durante 21 dias mejora significativamente tu estado de animo."
        ),
    },
    {
        "title": "Caminata consciente",
        "body": (
            "Camina durante 15 minutos sin celular. Presta atencion a cada paso, "
            "al aire en tu piel, a los sonidos alrededor. El ejercicio fisico, "
            "aunque sea suave, libera endorfinas naturales que mejoran tu humor."
        ),
    },
    {
        "title": "Desconexion digital",
        "body": (
            "Dedica los ultimos 30 minutos antes de dormir sin pantallas. "
            "Lee, estira o simplemente respira profundo. La luz azul de los dispositivos "
            "interfiere con la melatonina y afecta la calidad de tu sueño."
        ),
    },
    {
        "title": "Conexion humana",
        "body": (
            "Escribe un mensaje a alguien que quieras. No necesitas una razon especial. "
            "Un simple 'pense en ti' puede fortalecer tus relaciones y reducir "
            "sentimientos de soledad. La conexion social es fundamental para la salud mental."
        ),
    },
    {
        "title": "Hidratacion y animo",
        "body": (
            "Beber al menos 6 vasos de agua al dia puede mejorar tu concentracion "
            "y estado de animo. La deshidratacion leve afecta directamente tus "
            "funciones cognitivas y puede generar sensacion de fatiga."
        ),
    },
    {
        "title": "Celebracion consciente",
        "body": (
            "Haz una pausa y reconoce algo que lograste hoy, por pequeño que sea. "
            "Completar una tarea, ser amable con alguien, o simplemente haber hecho "
            "tu mejor esfuerzo cuenta. El auto-reconocimiento fortalece la autoestima."
        ),
    },
    {
        "title": "Respiracion diafragmatica",
        "body": (
            "Coloca una mano en tu pecho y otra en tu abdomen. Inhala profundamente "
            "por la nariz sintiendo como se expande tu abdomen (no el pecho). "
            "Exhala lento por la boca. 5 minutos de esta practica reducen el cortisol."
        ),
    },
    {
        "title": "Aprendizaje continuo",
        "body": (
            "Dedica 10 minutos a aprender algo nuevo: un idioma, una receta, "
            "un instrumento. El cerebro necesita estimulacion constante para mantenerse "
            "saludable. La neuroplasticidad se activa con la novedad."
        ),
    },
    {
        "title": "Amabilidad hacia ti",
        "body": (
            "Habla contigo mismo como lo hariás con un buen amigo. "
            "Si te equivocas, en lugar de criticarte, preguntate: "
            "que le diria a alguien que quiero en esta situacion? "
            "La autocompasion es una habilidad que se puede entrenar."
        ),
    },
]


class Command(BaseCommand):
    help = "Envia un correo diario de wellness tips a todos los suscriptores activos del newsletter."

    def handle(self, *args, **options):
        today = date.today()
        tip = DAILY_TIPS[today.toordinal() % len(DAILY_TIPS)]

        subscribers = list(
            NewsletterSubscriber.objects.filter(is_active=True).values_list("email", flat=True)
        )

        if not subscribers:
            self.stdout.write(self.style.WARNING("No hay suscriptores activos."))
            return

        subject = f"PsyAI Connect - Tip del dia: {tip['title']}"
        from_email = settings.DEFAULT_FROM_EMAIL or "PsyAI Connect <noreply@psyaiconnect.com>"

        html_message = render_to_string(
            "emails/newsletter_daily_tip.html",
            {"tip": tip, "date": today},
        )

        plain_message = f"""PsyAI Connect - Tip del dia

{tip['title']}

{tip['body']}

---
Gracias por suscribirte al newsletter de PsyAI Connect.
Tu bienestar emocional es nuestra prioridad.

Si ya no deseas recibir estos correos, responde con "cancelar"."""

        sent = 0
        failed = 0

        for email in subscribers:
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message,
                    from_email=from_email,
                    to=[email],
                )
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently=False)
                sent += 1
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Error enviando a {email}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Enviados: {sent}/{len(subscribers)} | Fallidos: {failed} | Tip: {tip['title']}"
            )
        )
