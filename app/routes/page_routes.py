import os

from flask import Blueprint, current_app, send_from_directory, render_template, request, session, redirect


pages_bp = Blueprint("pages", __name__)


def _template_root():
    return os.path.join(current_app.root_path, current_app.template_folder or "templates")


def _static_root():
    return os.path.join(current_app.root_path, "static")


@pages_bp.route("/")
@pages_bp.route("/index.html")
def index():
    return render_template("base/index.html")


@pages_bp.route("/recover")
def recover_with_token():
    token = request.args.get("token")
    if token:
        return render_template("auth/reset-password.html")
    return render_template("auth/recover.html")


PAGES_LEGAL = {
    "privacidad": {"title": "Política de Privacidad", "template": "legal/privacidad.html"},
    "terminos": {"title": "Términos y Condiciones", "template": "legal/terminos.html"},
    "cookies": {"title": "Política de Cookies", "template": "legal/cookies.html"},
}

@pages_bp.route("/<path:filename>")
def serve_pages(filename: str):
    """
    Compat layer: previously every .html lived in repo root and could be fetched
    directly (e.g. /login.html, /aside-admin/users.html).
    After refactor, we keep URLs stable and map to app/templates/*.
    """
    user_role = session.get("rol")

    # Legal pages
    if filename.startswith("legal/"):
        page = filename.removeprefix("legal/").removesuffix("/")
        if page in PAGES_LEGAL:
            info = PAGES_LEGAL[page]
            return render_template(info["template"], title=info["title"], updated="18 de junio de 2026")
        return redirect("/")

    # Enforce role-based access control for templates
    if filename == "admin.dashboard.html" or filename.startswith("aside-admin/"):
        if user_role != "admin":
            return redirect("/login.html")

    if filename == "patient.dashboard.html" or filename.startswith("aside-patient/"):
        if user_role != "paciente":
            return redirect("/login.html")

    if filename == "professional.dashboard.html" or filename.startswith("aside-professional/"):
        if user_role != "profesional":
            return redirect("/login.html")

    root = _template_root()

    direct_map = {
        "index.html": "base/index.html",
        "login.html": "auth/login.html",
        "register.html": "auth/register.html",
        "recover.html": "auth/recover.html",
        "reset-password.html": "auth/reset-password.html",
        "admin.dashboard.html": "admin/admin.dashboard.html",
        "patient.dashboard.html": "patient/patient.dashboard.html",
        "professional.dashboard.html": "professional/professional.dashboard.html",
    }

    if filename in direct_map:
        return render_template(direct_map[filename])

    if filename.startswith("aside-admin/"):
        rel = "admin/aside-admin/" + filename.removeprefix("aside-admin/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return render_template(rel)

    if filename.startswith("aside-patient/"):
        rel = "patient/aside-patient/" + filename.removeprefix("aside-patient/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return render_template(rel)

    if filename.startswith("aside-professional/"):
        rel = "professional/aside-professional/" + filename.removeprefix("aside-professional/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return render_template(rel)

    # fallback: allow direct lookup inside templates root (for any other html)
    if os.path.exists(os.path.join(root, filename)):
        return render_template(filename)

    # serve legacy static paths (css/js/img/responsive/uploads/etc)
<<<<<<< HEAD
    return send_from_directory(_static_root(), filename)
=======
    if filename.startswith("uploads/"):
        cache_max_age = 0
    elif any(filename.startswith(p) for p in ("css/", "js/", "img/", "responsive/")):
        cache_max_age = 86400
    else:
        cache_max_age = None
    return send_from_directory(_static_root(), filename, max_age=cache_max_age)
>>>>>>> 629d7c0 (avances)
