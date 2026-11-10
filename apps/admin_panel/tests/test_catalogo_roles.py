"""Pruebas del catálogo de roles personalizados (HU-11)."""
import json

import pytest

from apps.admin_panel import roles
from apps.admin_panel.models import Logs
from apps.admin_panel.services import AdminService
from apps.authentication.models import Register, RolPersonalizado
from apps.authentication.security import SecurityHelper


def _usuario(email, rol, nombre="Usuario"):
    return Register.objects.create(
        nombre=nombre, email=email, contrasena=SecurityHelper.hash_password("Clave123*"),
        rol=rol, activo=True, estadoCuenta="Activa",
    )


def _login(client, email, rol):
    r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                    content_type="application/json")
    assert r.status_code == 200


class TestCrear:
    def test_crea_rol_sobre_una_base(self):
        payload, status = roles.crear({"nombre": " Psicólogo  clínico ", "rolBase": "profesional",
                                       "descripcion": "Atiende terapia individual"}, "Admin Demo")

        assert status == 201
        assert payload["rol"]["nombre"] == "Psicólogo clínico"
        assert payload["rol"]["rolBaseNombre"] == "Profesional"
        assert Logs.objects.filter(modulo="roles", accion="Crear rol").exists()

    @pytest.mark.parametrize("datos", [
        {"nombre": "ab", "rolBase": "profesional"},
        {"nombre": "x" * 41, "rolBase": "profesional"},
        {"nombre": "Coordinador", "rolBase": "superusuario"},
        {"nombre": "Administrador", "rolBase": "admin"},
    ])
    def test_datos_invalidos(self, datos):
        assert roles.crear(datos)[1] == 400

    def test_nombre_repetido(self):
        roles.crear({"nombre": "Coordinador", "rolBase": "admin"})

        assert roles.crear({"nombre": "coordinador", "rolBase": "admin"})[1] == 400


class TestAsignarYEliminar:
    def test_asignar_rol_personalizado_hereda_la_base(self):
        usuario = _usuario("ana@test.com", "paciente", "Ana")
        rol = RolPersonalizado.objects.create(nombre="Psicólogo clínico", rolBase="profesional")

        payload, status = AdminService().change_role({"idUsuario": usuario.idUsuario, "nuevoRol": f"custom:{rol.idRol}"})

        assert status == 200
        usuario.refresh_from_db()
        assert usuario.rol == "profesional"  # los permisos son los de la base
        assert usuario.rol_nombre == "Psicólogo clínico"
        log = Logs.objects.get(accion="Cambio de rol")
        assert "Paciente -> Psicólogo clínico" in log.detalle

    def test_volver_a_un_rol_base_quita_el_personalizado(self):
        rol = RolPersonalizado.objects.create(nombre="Practicante", rolBase="profesional")
        usuario = _usuario("ana@test.com", "profesional")
        usuario.rolPersonalizado = rol
        usuario.save()

        AdminService().change_role({"idUsuario": usuario.idUsuario, "nuevoRol": "paciente"})

        usuario.refresh_from_db()
        assert usuario.rolPersonalizado is None
        assert usuario.rol_nombre == "Paciente"

    def test_rol_inexistente(self):
        usuario = _usuario("ana@test.com", "paciente")

        assert AdminService().change_role({"idUsuario": usuario.idUsuario, "nuevoRol": "custom:999"})[1] == 400

    def test_no_se_elimina_un_rol_con_usuarios(self):
        rol = RolPersonalizado.objects.create(nombre="Practicante", rolBase="profesional")
        usuario = _usuario("ana@test.com", "profesional")
        usuario.rolPersonalizado = rol
        usuario.save()

        payload, status = roles.eliminar(rol.idRol)

        assert status == 400
        assert "1 usuario" in payload["message"]
        assert RolPersonalizado.objects.filter(pk=rol.pk).exists()

    def test_elimina_un_rol_sin_usuarios(self):
        rol = RolPersonalizado.objects.create(nombre="Practicante", rolBase="profesional")

        assert roles.eliminar(rol.idRol, "Admin")[1] == 200
        assert not RolPersonalizado.objects.exists()
        assert Logs.objects.filter(accion="Eliminar rol").exists()

    def test_catalogo_cuenta_usuarios(self):
        rol = RolPersonalizado.objects.create(nombre="Practicante", rolBase="profesional")
        u = _usuario("ana@test.com", "profesional")
        u.rolPersonalizado = rol
        u.save()
        _usuario("pac@test.com", "paciente")

        payload, _ = roles.catalogo()

        base = {r["rolBase"]: r["usuarios"] for r in payload["base"]}
        assert base["paciente"] == 1 and base["profesional"] == 0
        assert payload["personalizados"][0]["usuarios"] == 1


def test_api_y_sesion_muestran_el_rol(client):
    _usuario("admin@test.com", "admin", "Admin")
    usuario = _usuario("pro@test.com", "profesional", "Dra. Ruiz")
    _login(client, "admin@test.com", "admin")

    r = client.post("/api/admin/roles/catalogo", data=json.dumps({"nombre": "Psicólogo clínico", "rolBase": "profesional"}),
                    content_type="application/json")
    assert r.status_code == 201
    id_rol = r.json()["rol"]["idRol"]
    r = client.patch(f"/api/admin/usuarios/{usuario.idUsuario}", data=json.dumps({"nuevoRol": f"custom:{id_rol}"}),
                     content_type="application/json")
    assert r.status_code == 200
    fila = next(u for u in client.get("/api/admin/usuarios").json()["usuarios"] if u["email"] == "pro@test.com")
    assert fila["rolPersonalizado"] == "Psicólogo clínico"

    _login(client, "pro@test.com", "profesional")
    assert client.get("/api/session").json()["usuario"]["rolNombre"] == "Psicólogo clínico"
    assert client.get("/api/profesional/calificaciones").status_code == 200  # hereda los permisos de profesional
    assert client.get("/api/admin/roles/catalogo").status_code == 403
