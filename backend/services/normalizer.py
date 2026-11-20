from rapidfuzz import fuzz, process
from .. import db
from ..schemas import Item


def normalizar(items: list[Item]) -> list[Item]:
    with db.conn() as c:
        alias = {r["alias"]: r["nombre"] for r in c.execute("SELECT * FROM alias")}
        conocidos = [r["nombre"] for r in c.execute("SELECT nombre FROM productos")]
    for it in items:
        k = it.nombre.strip().lower()
        if k in alias:
            it.nombre = alias[k]
        elif conocidos:
            m = process.extractOne(k, conocidos, scorer=fuzz.WRatio)
            if m and m[1] >= 85:
                it.nombre = m[0]
            else:
                it.confianza = min(it.confianza, 0.6)   # producto nuevo: que lo revisen
    return items
