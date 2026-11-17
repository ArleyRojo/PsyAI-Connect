"""
Prueba guardiana de la arquitectura en capas.

Solo los repositorios (y los modelos) hablan con la base de datos. Si alguien escribe
`Modelo.objects...` o SQL directo en una vista, un servicio u otro módulo, esta prueba
falla y dice en qué archivo y línea está, para moverlo al repositorio de su app.
"""
import re
from pathlib import Path

APPS = Path(__file__).resolve().parents[2]

# Archivos donde sí puede ir el ORM
PERMITIDOS = {"models.py", "repositories.py"}
CARPETAS_IGNORADAS = {"tests", "migrations", "__pycache__"}

# SQL directo que se deja fuera del repositorio a propósito
SQL_PERMITIDO = {
    "admin_panel/copias.py": "restaurar copia: vaciar tablas dentro de la transacción",
    "admin_panel/mantenimiento.py": "estado del sistema: SELECT 1 y tamaño de la base",
    "core/views.py": "health check: SELECT 1",
}

ORM = re.compile(r"\.objects\.")
SQL = re.compile(r"connection\.cursor\(|\.raw\(|\.extra\(")


def _archivos():
    for ruta in sorted(APPS.rglob("*.py")):
        partes = ruta.relative_to(APPS).parts
        if CARPETAS_IGNORADAS.intersection(partes) or ruta.name in PERMITIDOS:
            continue
        yield ruta


def buscar(texto, patron):
    """Números de línea donde aparece el patrón, sin contar comentarios."""
    return [n for n, linea in enumerate(texto.splitlines(), 1)
            if patron.search(linea.split("#", 1)[0])]


def _violaciones(patron, permitidos=()):
    encontradas = []
    for ruta in _archivos():
        relativa = ruta.relative_to(APPS).as_posix()
        if relativa in permitidos:
            continue
        for linea in buscar(ruta.read_text(encoding="utf-8"), patron):
            encontradas.append(f"apps/{relativa}:{linea}")
    return encontradas


def test_el_orm_solo_se_usa_en_los_repositorios():
    violaciones = _violaciones(ORM)
    assert not violaciones, (
        "Consultas ORM fuera de repositories.py; muévelas al repositorio de su app:\n"
        + "\n".join(violaciones)
    )


def test_el_sql_directo_solo_se_usa_en_los_repositorios():
    violaciones = _violaciones(SQL, SQL_PERMITIDO)
    assert not violaciones, (
        "SQL directo fuera de repositories.py; muévelo al repositorio de su app "
        "o agrégalo a SQL_PERMITIDO con el motivo:\n" + "\n".join(violaciones)
    )


def test_la_guardia_detecta_consultas():
    codigo = (
        "usuario = Register.objects.get(pk=1)\n"
        "# Register.objects.all() en un comentario no cuenta\n"
        "with connection.cursor() as c:\n"
    )
    assert buscar(codigo, ORM) == [1]
    assert buscar(codigo, SQL) == [3]


def test_los_permitidos_existen():
    """Si se borra o renombra un archivo de la lista, hay que quitarlo de aquí."""
    for relativa in SQL_PERMITIDO:
        assert (APPS / relativa).exists(), relativa
