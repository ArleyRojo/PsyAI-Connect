import os

from flask import Blueprint, current_app, send_from_directory, render_template


pages_bp = Blueprint("pages", __name__)


def _template_root():
    return os.path.join(current_app.root_path, current_app.template_folder or "templates")


def _static_root():
    return os.path.join(current_app.root_path, "static")


@pages_bp.route("/")
def index():
    return render_template("base/index.html")


@pages_bp.route("/<path:filename>")
def serve_pages(filename: str):
    """
    Compat layer: previously every .html lived in repo root and could be fetched
    directly (e.g. /login.html, /aside-admin/users.html).
    After refactor, we keep URLs stable and map to app/templates/*.
    """

    root = _template_root()

    direct_map = {
        "login.html": "auth/login.html",
        "register.html": "auth/register.html",
        "recover.html": "auth/recover.html",
        "admin.dashboard.html": "admin/admin.dashboard.html",
        "patient.dashboard.html": "patient/patient.dashboard.html",
        "professional.dashboard.html": "professional/professional.dashboard.html",
        "patients.html": "professional/aside-professional/patients.html",
        "index.html": "base/index.html",
    }

    if filename in direct_map:
        return send_from_directory(root, direct_map[filename])

    if filename.startswith("aside-admin/"):
        rel = "admin/aside-admin/" + filename.removeprefix("aside-admin/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return send_from_directory(root, rel)

    if filename.startswith("aside-patient/"):
        rel = "patient/aside-patient/" + filename.removeprefix("aside-patient/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return send_from_directory(root, rel)

    if filename.startswith("aside-professional/"):
        rel = "professional/aside-professional/" + filename.removeprefix("aside-professional/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return send_from_directory(root, rel)

    # fallback: allow direct lookup inside templates root (for any other html)
    if os.path.exists(os.path.join(root, filename)):
        return send_from_directory(root, filename)

    # serve legacy static paths (css/js/img/responsive/uploads/etc)
    return send_from_directory(_static_root(), filename)

