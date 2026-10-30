from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es requerido")
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        extra_fields.setdefault("rol", "admin")
        if extra_fields.get("rol") != "admin":
            raise ValueError("El superusuario debe tener rol admin")
        return self.create_user(email, nombre, password, **extra_fields)


class Register(AbstractBaseUser):
    ROL_CHOICES = [
        ("paciente", "Paciente"),
        ("profesional", "Profesional"),
        ("admin", "Admin"),
    ]
    ESTADO_CHOICES = [
        ("Activa", "Activa"),
        ("Suspendida", "Suspendida"),
    ]

    idUsuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    email = models.EmailField(unique=True, max_length=120)
    password = models.CharField(
        max_length=255, db_column="contrasena", verbose_name="contrasena"
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    fotoPerfil = models.CharField(max_length=255, null=True, blank=True)
    estadoCuenta = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="Activa"
    )
    activo = models.BooleanField(default=True)
    # Verificación de email
    email_verificado = models.BooleanField(default=False)
    fechaRegistro = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    @property
    def is_staff(self):
        return self.rol == "admin"

    @property
    def is_superuser(self):
        return self.rol == "admin"

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        db_table = "Register"

    @property
    def contrasena(self):
        return self.password

    @contrasena.setter
    def contrasena(self, value):
        self.password = value

    def __str__(self):
        return self.email

    def set_password(self, raw_password):
        from apps.authentication.security import SecurityHelper
        self.password = SecurityHelper.hash_password(raw_password)

    def check_password(self, raw_password):
        from apps.authentication.security import SecurityHelper
        return SecurityHelper.verify_password(raw_password, self.password)

    def to_dict(self):
        """Return user data safe for session storage (includes password hash for auth)."""
        return {
            "idUsuario": self.idUsuario,
            "nombre": self.nombre,
            "email": self.email,
            "contrasena": self.password,
            "rol": self.rol,
            "activo": self.activo,
            "estadoCuenta": self.estadoCuenta,
            "email_verificado": self.email_verificado,
            "fechaRegistro": (
                self.fechaRegistro.isoformat() if self.fechaRegistro else None
            ),
            "fotoPerfil": self.fotoPerfil,
        }

    def to_session_dict(self):
        """Return minimal user data for session storage (consistent across all auth flows)."""
        return {
            "id": self.idUsuario,
            "nombre": self.nombre,
            "email": self.email,
            "rol": self.rol,
            "fotoPerfil": self.fotoPerfil,
        }


class Login(models.Model):
    idLogin = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
    )
    email = models.CharField(max_length=120)
    contrasena = models.CharField(max_length=200, null=True, blank=True)
    ultimoAcceso = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Login"

    def to_dict(self):
        return {
            "idLogin": self.idLogin,
            "idUsuario": self.idUsuario_id,
            "email": self.email,
            "ultimoAcceso": (
                self.ultimoAcceso.isoformat() if self.ultimoAcceso else None
            ),
        }


class RecoveryTokens(models.Model):
    id = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
    )
    token = models.CharField(max_length=100, unique=True)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "RecoveryTokens"

    def to_dict(self):
        return {
            "id": self.id,
            "idUsuario": self.idUsuario_id,
            "token": self.token,
            "expires": self.expires.isoformat() if self.expires else None,
            "used": self.used,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
        }


class EmailVerificationToken(models.Model):
    """
    Token para verificación de email al registrarse.
    Requerido obligatoriamente para rol 'profesional', opcional para 'paciente'.
    """
    id = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
    )
    token = models.CharField(max_length=100, unique=True)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "EmailVerificationTokens"

    def to_dict(self):
        return {
            "id": self.id,
            "idUsuario": self.idUsuario_id,
            "token": self.token,
            "expires": self.expires.isoformat() if self.expires else None,
            "used": self.used,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
        }


class IntentosFallidos(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=255, unique=True)
    intentos = models.IntegerField(default=0)
    ultimo_intento = models.DateTimeField(null=True, blank=True)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "intentos_fallidos"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "intentos": self.intentos,
            "ultimo_intento": (
                self.ultimo_intento.isoformat() if self.ultimo_intento else None
            ),
            "bloqueado_hasta": (
                self.bloqueado_hasta.isoformat() if self.bloqueado_hasta else None
            ),
        }


class TOTPDevice(models.Model):
    """
    Dispositivo TOTP (Time-based One-Time Password) para autenticación de dos factores (2FA).
    Opcional para roles 'admin' y 'profesional'.
    Usa RFC 6238 / RFC 4226 compatible (compatible con Google Authenticator, Authy, etc.).
    """
    id = models.AutoField(primary_key=True)
    idUsuario = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
        related_name="totp_device",
    )
    # Secreto en base32 (RFC 3548), generado con secrets.token_bytes(20) y codificado en base32
    secret = models.CharField(max_length=64)
    # Nombre amigable del dispositivo (ej: "Mi móvil", "Authenticator")
    name = models.CharField(max_length=100, blank=True, default="")
    # Si el 2FA está confirmado/activo
    confirmed = models.BooleanField(default=False)
    # Fecha de creación
    createdAt = models.DateTimeField(auto_now_add=True)
    # Último uso exitoso
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "TOTPDevices"

    def to_dict(self):
        return {
            "id": self.id,
            "idUsuario": self.idUsuario_id,
            "name": self.name,
            "confirmed": self.confirmed,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class ConsentimientoUsuario(models.Model):
    """
    Registro de consentimientos del usuario según Ley 1581/2012.
    Cada vez que se actualizan los textos legales (LEGAL_VERSION),
    el usuario debe volver a aceptarlos.
    """
    TIPO_CHOICES = [
        ("terminos_privacidad", "Términos y Política de Privacidad"),
        ("datos_sensibles_ia", "Datos Sensibles e IA"),
        ("whatsapp", "WhatsApp / Notificaciones"),
    ]

    id = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
        related_name="consentimientos",
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    version = models.CharField(max_length=20, help_text="Versión del texto legal (LEGAL_VERSION)")
    aceptado = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    userAgent = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "ConsentimientoUsuario"
        unique_together = [("idUsuario", "tipo", "version")]
        indexes = [
            models.Index(fields=["idUsuario", "tipo"]),
            models.Index(fields=["fecha"]),
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "idUsuario": self.idUsuario_id,
            "tipo": self.tipo,
            "version": self.version,
            "aceptado": self.aceptado,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "ip": self.ip,
        }

    def __str__(self):
        return f"Consentimiento {self.tipo} v{self.version} - Usuario {self.idUsuario_id}"
