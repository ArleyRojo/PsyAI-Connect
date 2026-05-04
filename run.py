import os
import socket
import sys
import logging

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), '.env.example')
load_dotenv(env_path)

API_LIST = [
    ("POST", "/api/register"),
    ("POST", "/api/login"),
    ("POST", "/api/logout"),
    ("GET", "/api/session"),
    ("POST", "/api/recover"),
    ("POST", "/api/reset-password"),
    ("POST", "/api/admin/crear-columnas-diagnostico"),
    ("GET", "/api/admin/stats"),
    ("GET", "/api/admin/usuarios"),
    ("GET", "/api/admin/usuarios/<id>"),
    ("POST", "/api/admin/usuarios"),
    ("PUT", "/api/admin/usuarios/<id>"),
    ("DELETE", "/api/admin/usuarios/<id>"),
    ("PATCH", "/api/admin/usuarios/<id>/bloquear"),
    ("GET", "/api/admin/roles/usuarios"),
    ("PATCH", "/api/admin/usuarios/<id>/rol"),
    ("GET", "/api/admin/roles/historial"),
    ("GET", "/api/admin/notificaciones"),
    ("POST", "/api/admin/notificaciones"),
    ("DELETE", "/api/admin/notificaciones/<id>"),
    ("GET", "/api/admin/logs"),
    ("GET", "/api/perfil/paciente/<id>"),
    ("PUT", "/api/perfil/paciente"),
    ("POST", "/api/evolucion"),
    ("GET", "/api/evolucion"),
    ("GET", "/api/pacientes"),
    ("GET", "/api/profesionales"),
    ("GET", "/api/perfil/profesional/<id>"),
    ("PUT", "/api/perfil/profesional"),
    ("POST", "/api/disponibilidad"),
    ("GET", "/api/disponibilidad/<id>"),
    ("GET", "/api/profesional/dashboard"),
    ("GET", "/api/profesional/pacientes"),
    ("POST", "/api/diagnosticos"),
    ("GET", "/api/diagnosticos"),
    ("GET", "/api/reportes/profesional"),
    ("GET", "/api/reportes/eliminados"),
    ("POST", "/api/reportes"),
    ("PUT", "/api/reportes/<id>"),
    ("DELETE", "/api/reportes/<id>"),
    ("GET", "/api/evolucion/profesional"),
    ("POST", "/api/citas"),
    ("GET", "/api/citas/disponibles"),
    ("GET", "/api/citas/profesional"),
    ("GET", "/api/citas/profesional/horarios"),
    ("GET", "/api/citas/proxima"),
    ("GET", "/api/citas/solicitadas"),
    ("PATCH", "/api/citas/<id>/estado"),
    ("GET", "/api/citas/paciente"),
    ("DELETE", "/api/citas/<id>"),
    ("GET", "/api/citas/fechas-disponibles"),
    ("GET", "/healthz"),
]

STATIC_FILES = {
    "IMAGES": [
        "static/img/Psicologia2.jpg",
        "static/img/psicologia1.jpg",
        "static/img/Psicologia.jpg",
        "static/img/Logo.jpg",
    ],
    "JS": [
        "static/js/modules/auth/auth-guard.js",
        "static/js/modules/auth/logout.js",
        "static/js/modules/auth/login.js",
        "static/js/modules/auth/recover.js",
        "static/js/modules/auth/register.js",
        "static/js/modules/auth/auth-ui.js",
        "static/js/modules/professional/my.agenda.js",
        "static/js/modules/professional/patients.js",
        "static/js/modules/professional/my.profile2.js",
        "static/js/modules/professional/reports.js",
        "static/js/modules/professional/aside.js",
        "static/js/modules/admin/admin.logs.js",
        "static/js/modules/admin/admin.dashboard.js",
        "static/js/modules/admin/admin.users.js",
        "static/js/modules/admin/admin.notifications.js",
        "static/js/modules/admin/admin.roles.js",
        "static/js/modules/patient/chatbot.js",
        "static/js/modules/patient/my.profile.js",
        "static/js/modules/patient/evolution.js",
        "static/js/modules/patient/agendaquotes.js",
        "static/js/modules/patient/aside.js",
        "static/js/core/shared/alerts.js",
        "static/js/core/shared/theme-inline.js",
        "static/js/core/shared/nombre.usuario.js",
        "static/js/core/shared/localStorage-detector.js",
        "static/js/core/shared/theme.js",
        "static/js/core/shared/scroll-reveal.js",
        "static/js/core/shared/mobile-navbar-toggle.js",
        "static/js/core/shared/aside.js",
        "static/js/pages/index.js",
    ],
    "CSS": [
        "static/css/themes/theme.css",
        "static/css/components/components.css",
        "static/css/components/custom-alerts.css",
        "static/css/pages/auth.css",
        "static/css/pages/aside.css",
        "static/css/pages/aside-patient.css",
        "static/css/pages/admin.css",
        "static/css/pages/landing.css",
        "static/css/pages/patients.css",
        "static/css/pages/my.profile.css",
        "static/css/pages/my.profile2.css",
        "static/css/base/base.css",
        "static/css/base/animations.css",
        "static/css/layout/layout.css",
        "static/responsive/aside-patient.css",
        "static/responsive/professional.css",
        "static/responsive/layout.professional.css",
        "static/responsive/index.css",
        "static/responsive/evolution.css",
        "static/responsive/auth.css",
        "static/responsive/aside.css",
        "static/responsive/admin.css",
    ],
}


def print_app_info():
    print("\n" + "=" * 60)
    print("PsyAI Connect - Endpoints Disponibles")
    print("=" * 60)
    print("\n--- APIs (REST) ---")
    for method, path in API_LIST:
        print(f"  {method:6} {path}")
    print("\n--- Archivos Estaticos ---")
    for category, files in STATIC_FILES.items():
        print(f"\n  [{category}]")
        for f in files:
            print(f"    {f}")
    print("\n" + "=" * 60)


from app import create_app
from app.database.migrations import init_db


app = create_app()

with app.app_context():
    try:
        init_db()
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('flask-limiter').setLevel(logging.WARNING)
    logging.getLogger('werkzeug._internal').setLevel(logging.WARNING)
    
    print_app_info()
    app.run(debug=False, host="127.0.0.1", port=port, use_reloader=False, use_evalex=False)