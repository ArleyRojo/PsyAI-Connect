from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from apps.core.views import health_check, client_errors, serve_pages, error_404, error_500, error_403, newsletter_subscribe, theme_preference

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include("apps.authentication.urls")),
    path("api/", include("apps.patients.urls")),
    path("api/", include("apps.professionals.urls")),
    path("api/", include("apps.scheduling.urls")),
    path("api/", include("apps.chatbot.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/", include("apps.admin_panel.urls")),
    path("api/", include("apps.core.urls")),
    path("api/client-errors", client_errors, name="client_errors"),
    path("api/theme", theme_preference, name="theme_preference"),
    path("api/newsletter/subscribe", newsletter_subscribe, name="newsletter_subscribe"),
    path("health/", csrf_exempt(health_check), name="health"),
    path("healthz/", csrf_exempt(health_check), name="healthz"),
    # Sin barra final: si no, caen en serve_pages (catch-all) y responden 404.
    path("health", csrf_exempt(health_check), name="health_sin_barra"),
    path("healthz", csrf_exempt(health_check), name="healthz_sin_barra"),
    path("", serve_pages, {"filename": "index.html"}, name="index"),
    path("<path:filename>", serve_pages, name="page_catch_all"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static("/uploads/", document_root=settings.MEDIA_ROOT / "uploads")

handler404 = error_404
handler500 = error_500
handler403 = error_403
