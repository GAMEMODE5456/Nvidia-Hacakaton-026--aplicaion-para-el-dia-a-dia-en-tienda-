"""Asistente de NAVEGACION. ROL B reemplaza el mock por base + LoRA (misma interfaz)."""
import unicodedata
from ..schemas import Accion


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


REGLAS = [  # (palabras clave, destino, mensaje)
    (("ticket", "escanear", "escaneo", "foto", "factura", "nota de compra", "recibo"),
     "escanear_ticket", "Abriendo escanear ticket."),
    (("inventario", "existencias", "mis productos", "que tengo", "cuanto tengo", "stock"),
     "inventario", "Abriendo su inventario."),
    (("inicio", "menu", "regresar", "volver", "atras", "pantalla principal"),
     "inicio", "Volviendo al inicio."),
]


class MockLLM:
    info = {"mock": True}

    def interpret(self, texto: str) -> Accion:
        t = _norm(texto).strip()
        if len(t) < 3:
            return Accion(accion="aclarar", mensaje="No le entendí. ¿Qué desea hacer?")
        for claves, destino, msg in REGLAS:
            if any(k in t for k in claves):
                if t.startswith(("como", "que hago", "ayuda", "no se")):
                    return Accion(accion="ayuda", destino=destino,
                                  mensaje=f"Le muestro dónde. {msg}")
                return Accion(accion="navegar", destino=destino, mensaje=msg)
        if any(k in t for k in ("ayuda", "como funciona", "no se", "que puedo hacer")):
            return Accion(accion="ayuda", mensaje="Puedo abrir escanear ticket, "
                          "su inventario o el inicio. ¿Cuál desea?")
        return Accion(accion="fuera_de_alcance",
                      mensaje="Solo puedo ayudarle a moverse en la aplicación.")


class RealLLM:
    def __init__(self):
        # TODO (rol B): cargar modelo base + adaptador LoRA; guardar sha256 en self.info
        raise NotImplementedError

    def interpret(self, texto: str) -> Accion:
        raise NotImplementedError


def load(mock: bool):
    return MockLLM() if mock else RealLLM()
