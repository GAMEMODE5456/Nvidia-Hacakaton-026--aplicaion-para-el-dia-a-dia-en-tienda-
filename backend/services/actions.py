"""UNICO modulo que escribe en el inventario (solo desde el flujo de ticket confirmado).
Ni el LLM ni el OCR tocan la BD."""
from .. import db
from ..schemas import Item, Resultado


def _siguiente_lote(c) -> int:
    return (c.execute("SELECT COALESCE(MAX(lote),0)+1 FROM movimientos").fetchone()[0])


def _aplicar(c, nombre: str, delta: float, lote: int, motivo: str, precio=None):
    c.execute("INSERT OR IGNORE INTO productos(nombre, cantidad) VALUES(?, 0)", (nombre,))
    c.execute("UPDATE productos SET cantidad = cantidad + ?, "
              "precio = COALESCE(?, precio) WHERE nombre = ?", (delta, precio, nombre))
    c.execute("INSERT INTO movimientos(lote, producto, delta, motivo) VALUES(?,?,?,?)",
              (lote, nombre, delta, motivo))


def bulk_add(items: list[Item], motivo="ticket") -> Resultado:
    if not items:
        return Resultado(ok=False, mensaje="No hay productos para guardar.")
    with db.conn() as c:
        lote = _siguiente_lote(c)
        for it in items:
            _aplicar(c, it.nombre.strip().lower(), it.cantidad, lote, motivo, it.precio)
    return Resultado(ok=True, lote=lote, mensaje=f"Listo. Se agregaron {len(items)} productos.")


def undo(lote: int) -> Resultado:
    with db.conn() as c:
        movs = c.execute("SELECT producto, delta FROM movimientos "
                         "WHERE lote=? AND deshecho=0", (lote,)).fetchall()
        if not movs:
            return Resultado(ok=False, mensaje="No hay nada que deshacer.")
        for m in movs:
            c.execute("UPDATE productos SET cantidad = cantidad - ? WHERE nombre=?",
                      (m["delta"], m["producto"]))
        c.execute("UPDATE movimientos SET deshecho=1 WHERE lote=?", (lote,))
    return Resultado(ok=True, mensaje="Listo. Se deshizo el cambio.")
