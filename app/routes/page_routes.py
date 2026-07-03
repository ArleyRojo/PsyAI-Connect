import os

from flask import Blueprint, current_app, send_from_directory, render_template, request, session, redirect
from flask.views import MethodView


pages_bp = Blueprint("pages", __name__)


class PageRouteHelpers:
    @staticmethod
    def template_root():
        return os.path.join(current_app.root_path, current_app.template_folder or "templates")

    @staticmethod
    def static_root():
        return os.path.join(current_app.root_path, "static")


PAGES_LEGAL = {
    "privacidad": {"title": "Pol\u00edtica de Privacidad", "template": "legal/privacidad.html"},
    "terminos": {"title": "T\u00e9rminos y Condiciones", "template": "legal/terminos.html"},
    "cookies": {"title": "Pol\u00edtica de Cookies", "template": "legal/cookies.html"},
}


class IndexView(MethodView):
    def get(self):
        return render_template("base/index.html")


class RecoverView(MethodView):
    def get(self):
        token = request.args.get("token")
        if token:
            return render_template("auth/reset-password.html")
        return render_template("auth/recover.html")


class ServePagesView(MethodView):
    def get(self, filename):
        user_role = session.get("rol")

        if filename.startswith("legal/"):
            page = filename.removeprefix("legal/").removesuffix("/")
            if page in PAGES_LEGAL:
                info = PAGES_LEGAL[page]
                return render_template(info["template"], title=info["title"], updated="18 de junio de 2026")
            return redirect("/")

        if filename == "admin.dashboard.html" or filename.startswith("aside-admin/"):
            if user_role != "admin":
                return redirect("/login.html")

        if filename == "patient.dashboard.html" or filename.startswith("aside-patient/"):
            if user_role != "paciente":
                return redirect("/login.html")

        if filename == "professional.dashboard.html" or filename.startswith("aside-professional/"):
            if user_role != "profesional":
                return redirect("/login.html")

        root = PageRouteHelpers.template_root()

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

        if os.path.exists(os.path.join(root, filename)):
            return render_template(filename)

        if filename.startswith("uploads/"):
            cache_max_age = 0
        elif any(filename.startswith(p) for p in ("css/", "js/", "img/", "responsive/")):
            cache_max_age = 86400
        else:
            cache_max_age = None
        return send_from_directory(PageRouteHelpers.static_root(), filename, max_age=cache_max_age)


pages_bp.add_url_rule("/", view_func=IndexView.as_view("index"))
pages_bp.add_url_rule("/index.html", view_func=IndexView.as_view("index_html"))
pages_bp.add_url_rule("/recover", view_func=RecoverView.as_view("recover"))
pages_bp.add_url_rule("/<path:filename>", view_func=ServePagesView.as_view("serve_pages"))
