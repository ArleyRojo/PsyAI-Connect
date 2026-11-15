"""Candado de arquitectura: Views -> Services -> Repositories -> PostgreSQL.

Falla si hay acceso al ORM fuera de repositories.py / models.py / migrations / tests:
  - `Modelo.objects...`
  - `Modelo.obtener()` (singletons de configuracion que consultan la BD)

PENDIENTES = archivos que aun no se migraron. Al migrar uno, BORRALO de la lista.
  - Un archivo que NO esta en la lista y usa ORM  -> falla (no se puede empeorar).
  - Un archivo que esta en la lista y ya no usa ORM -> falla (te obliga a limpiar la lista).
Cuando PENDIENTES quede vacia, la regla se cumple y el test queda como proteccion permanente.
"""
import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
IGNORAR_DIRS = {"migrations", "tests", "static", ".git", "legacy", "__pycache__"}
IGNORAR_ARCHIVOS = {"repositories.py", "models.py", "conftest.py"}
# copias.py: backup/restauracion con dumpdata/loaddata y SQL crudo (infraestructura, no consulta de modelos).
EXCEPCIONES_PERMANENTES = {"apps/admin_panel/copias.py"}
ACCESORES_SINGLETON = {"obtener"}

PENDIENTES = set()


def _usa_orm(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr == "objects":
            return True
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in ACCESORES_SINGLETON
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id[:1].isupper()
        ):
            return True
    return False


def _archivos_con_orm():
    res = set()
    for p in (ROOT / "apps").rglob("*.py"):
        rel = p.relative_to(ROOT)
        if IGNORAR_DIRS & set(rel.parts) or p.name in IGNORAR_ARCHIVOS:
            continue
        if rel.as_posix() in EXCEPCIONES_PERMANENTES:
            continue
        if _usa_orm(p):
            res.add(rel.as_posix())
    return res


def test_no_aparece_orm_nuevo_fuera_de_repositories():
    nuevos = _archivos_con_orm() - PENDIENTES
    assert not nuevos, f"ORM fuera de repositories.py en: {sorted(nuevos)}"


def test_lista_de_pendientes_esta_al_dia():
    ya_limpios = PENDIENTES - _archivos_con_orm()
    assert not ya_limpios, f"Ya sin ORM, borralos de PENDIENTES: {sorted(ya_limpios)}"
