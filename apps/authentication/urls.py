from django.urls import path

from apps.authentication.views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    ResetPasswordView,
    SessionView,
    CsrfTokenView,
    VerifyEmailView,
    TOTPSetupView,
    TOTPConfirmView,
    TOTPDisableView,
    TOTPStatusView,
    TOTPVerifyLoginView,
    social_login_redirect,
)

app_name = "authentication"

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf_token"),
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("session", SessionView.as_view(), name="session"),
    path("forgot-password", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password", ResetPasswordView.as_view(), name="reset_password"),
    path("verify-email", VerifyEmailView.as_view(), name="verify_email"),
    # TOTP / 2FA endpoints
    path("totp/setup", TOTPSetupView.as_view(), name="totp_setup"),
    path("totp/confirm", TOTPConfirmView.as_view(), name="totp_confirm"),
    path("totp/disable", TOTPDisableView.as_view(), name="totp_disable"),
    path("totp/status", TOTPStatusView.as_view(), name="totp_status"),
    path("totp/verify-login", TOTPVerifyLoginView.as_view(), name="totp_verify_login"),
    path("social-redirect", social_login_redirect, name="social_redirect"),
]
