from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from apps.core.views import health_check, client_errors, serve_pages, error_404, error_500, error_403, newsletter_subscribe

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
    path("api/client-errors", client_errors, name="client_errors"),
    path("api/newsletter/subscribe", newsletter_subscribe, name="newsletter_subscribe"),
    path("healthz/", csrf_exempt(health_check), name="healthz"),
    path("", serve_pages, {"filename": "index.html"}, name="index"),
    path("<path:filename>", serve_pages, name="page_catch_all"),
]

handler404 = error_404
handler500 = error_500
handler403 = error_403
