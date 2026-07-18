from django.urls import path

from apps.authentication.views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    ResetPasswordView,
    SessionView,
)

app_name = "authentication"

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("session", SessionView.as_view(), name="session"),
    path("forgot-password", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password", ResetPasswordView.as_view(), name="reset_password"),
]
