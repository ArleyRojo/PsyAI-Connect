"""
Copias de seguridad de la base de datos (HU-30 / HU-31, RN-17).

- Se exportan los datos con `dumpdata` de Django (JSON), se comprimen con gzip y se cifran
  con Fernet (clave derivada de BACKUP_KEY o, si no existe, de SECRET_KEY).
- Se guardan en BACKUP_DIR (carpeta `backups/`, en Docker un volumen compartido entre app y scheduler).
- El listado sale de los archivos, así restaurar una copia vieja no "borra" las copias más nuevas.
- Se guardan las últimas MAX_COPIAS. Automática una vez al día a la hora configurada.
- Restaurar: solo el admin, escribiendo RESTAURAR; antes se crea una copia del estado actual.
  Las sesiones no se tocan, así nadie pierde la sesión al restaurar.
"""
import base64
import gzip
import hashlib
import io
import logging
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_COPIAS = 7
CONFIRMACION = "RESTAURAR"
TIPOS = {"auto": "Automática", "manual": "Manual", "previa": "Antes de restaurar"}
PATRON = re.compile(r"^psyai_(\d{8})_(\d{6})_(auto|manual|previa)\.psyai$")

# Lo que no se copia: tablas internas de Django que se regeneran solas y las sesiones abiertas
EXCLUIR_MODELOS = {"contenttypes.contenttype", "auth.permission", "sessions.session", "admin.logentry"}
APPS_EXCLUIDAS = {"contenttypes", "sessions", "admin", "messages", "staticfiles"}


def carpeta():
    ruta = Path(getattr(settings, "BACKUP_DIR", None) or Path(settings.BASE_DIR) / "backups")
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _fernet():
    secreto = os.getenv("BACKUP_KEY") or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secreto.encode()).digest()))


def _modelos():
    """Modelos que entran en la copia (en el orden de las apps instaladas)."""
    modelos = []
    for config in apps.get_app_configs():
        if config.label in APPS_EXCLUIDAS:
            continue
        for modelo in config.get_models():
            if modelo._meta.label_lower in EXCLUIR_MODELOS or not modelo._meta.managed or modelo._meta.proxy:
                continue
            modelos.append(modelo)
    return modelos


# ── Listado ────────────────────────────────────────────────────────────────
def _info(archivo):
    m = PATRON.match(archivo.name)
    if not m:
        return None
    fecha = timezone.make_aware(datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S"))
    return {
        "archivo": archivo.name,
        "fecha": fecha.isoformat(),
        "tipo": TIPOS[m.group(3)],
        "clave": m.group(3),
        "tamano": archivo.stat().st_size,
    }


def listar():
    copias = [i for i in (_info(a) for a in carpeta().iterdir() if a.is_file()) if i]
    return sorted(copias, key=lambda c: c["archivo"][6:21], reverse=True)


def hay_copia_automatica_hoy():
    hoy = timezone.localdate().strftime("%Y%m%d")
    return any(c["clave"] == "auto" and c["archivo"][6:14] == hoy for c in listar())


def _rotar():
    for copia in listar()[MAX_COPIAS:]:
        try:
            (carpeta() / copia["archivo"]).unlink()
        except OSError as e:
            logger.warning("No se pudo borrar la copia vieja %s: %s", copia["archivo"], e)


# ── Crear ──────────────────────────────────────────────────────────────────
def crear(tipo="manual"):
    """Crea una copia cifrada. Devuelve la info de la copia."""
    salida = io.StringIO()
    etiquetas = [m._meta.label for m in _modelos()]
    call_command("dumpdata", *etiquetas, natural_foreign=True, stdout=salida)
    contenido = gzip.compress(salida.getvalue().encode("utf-8"))
    cifrado = _fernet().encrypt(contenido)

    # La hora del nombre es la local (Colombia) para que coincida con lo que ve el admin
    archivo = carpeta() / f"psyai_{timezone.localtime().strftime('%Y%m%d_%H%M%S')}_{tipo}.psyai"
    while archivo.exists():  # dos copias en el mismo segundo
        time.sleep(1)
        archivo = carpeta() / f"psyai_{timezone.localtime().strftime('%Y%m%d_%H%M%S')}_{tipo}.psyai"
    archivo.write_bytes(cifrado)
    _rotar()
    info = _info(archivo)
    info["fecha"] = timezone.localtime().isoformat()
    return info


# ── Restaurar ──────────────────────────────────────────────────────────────
def _leer(nombre):
    if not PATRON.match(nombre or ""):
        raise ValueError("Copia no encontrada")
    ruta = carpeta() / nombre
    if not ruta.exists():
        raise ValueError("Copia no encontrada")
    try:
        return gzip.decompress(_fernet().decrypt(ruta.read_bytes()))
    except InvalidToken:
        raise ValueError("No se pudo descifrar la copia (¿cambió la clave SECRET_KEY/BACKUP_KEY?)")


def restaurar(nombre):
    """Reemplaza los datos actuales por los de la copia (todo o nada)."""
    datos = _leer(nombre)
    tablas = [m._meta.db_table for m in _modelos()]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp.write(datos)
        ruta_tmp = tmp.name
    try:
        with transaction.atomic():
            sentencias = connection.ops.sql_flush(no_style(), tablas, reset_sequences=False, allow_cascade=True)
            with connection.cursor() as cursor:
                postgres = connection.vendor == "postgresql"
                if postgres:
                    # Revisa ya las llaves foráneas pendientes; si no, PostgreSQL no deja vaciar las tablas
                    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                for sql in sentencias:
                    cursor.execute(sql)
                if postgres:
                    cursor.execute("SET CONSTRAINTS ALL DEFERRED")
            call_command("loaddata", ruta_tmp, verbosity=0)
    finally:
        os.unlink(ruta_tmp)
