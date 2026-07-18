from django.contrib import admin

from apps.authentication.models import (
    IntentosFallidos,
    Login,
    RecoveryTokens,
    Register,
)


@admin.register(Register)
class RegisterAdmin(admin.ModelAdmin):
    list_display = ("email", "nombre", "rol", "estadoCuenta", "activo", "fechaRegistro")
    list_filter = ("rol", "estadoCuenta", "activo")
    search_fields = ("email", "nombre")
    ordering = ("-fechaRegistro",)
    fieldsets = (
        (None, {"fields": ("email", "contrasena")}),
        ("Info", {"fields": ("nombre", "rol", "fotoPerfil")}),
        ("Estado", {"fields": ("estadoCuenta", "activo")}),
    )
    readonly_fields = ("fechaRegistro",)


@admin.register(Login)
class LoginAdmin(admin.ModelAdmin):
    list_display = ("idLogin", "idUsuario", "email", "ultimoAcceso")
    search_fields = ("email",)
    readonly_fields = ("ultimoAcceso",)


@admin.register(RecoveryTokens)
class RecoveryTokensAdmin(admin.ModelAdmin):
    list_display = ("id", "idUsuario", "token", "expires", "used", "createdAt")
    list_filter = ("used",)
    readonly_fields = ("createdAt",)


@admin.register(IntentosFallidos)
class IntentosFallidosAdmin(admin.ModelAdmin):
    list_display = ("email", "intentos", "ultimo_intento", "bloqueado_hasta")
    search_fields = ("email",)
