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
    contrasena = models.CharField(max_length=200)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    fotoPerfil = models.CharField(max_length=255, null=True, blank=True)
    estadoCuenta = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="Activa"
    )
    activo = models.BooleanField(default=True)
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

    def __str__(self):
        return self.email

    def to_dict(self):
        return {
            "idUsuario": self.idUsuario,
            "nombre": self.nombre,
            "email": self.email,
            "contrasena": self.contrasena,
            "rol": self.rol,
            "activo": self.activo,
            "estadoCuenta": self.estadoCuenta,
            "fechaRegistro": (
                self.fechaRegistro.isoformat() if self.fechaRegistro else None
            ),
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
