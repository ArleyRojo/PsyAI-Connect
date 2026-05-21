from flask import Blueprint, jsonify, make_response, request


theme_bp = Blueprint("theme", __name__)


@theme_bp.route("/api/theme", methods=["GET", "POST"])
def api_theme():
    if request.method == "POST":
        theme = (request.json or {}).get("theme", "light")
        resp = make_response(jsonify({"success": True}))
        resp.set_cookie("theme", theme, max_age=365 * 24 * 60 * 60, samesite="Lax", httponly=False)
        return resp

    theme = request.cookies.get("theme", "light")
    is_dark = theme == "dark"
    if is_dark:
        bg, fg = "#030610", "#daeeff"
    else:
        bg, fg = "#ffffff", "#212529"
    return jsonify({"theme": theme, "dark": is_dark, "bg": bg, "fg": fg})

