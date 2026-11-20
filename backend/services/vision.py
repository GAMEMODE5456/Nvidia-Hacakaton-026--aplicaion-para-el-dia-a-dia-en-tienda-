"""Vision. ROL A reemplaza el mock por YOLO ajustado + OCR (misma interfaz)."""
import hashlib
import os
from ..schemas import Item, ParsedTicket


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class MockVision:
    info = {"mock": True}

    def parse(self, imagen: bytes) -> ParsedTicket:
        if not imagen:
            raise ValueError("imagen vacia")
        return ParsedTicket(items=[
            Item(nombre="agua 600 ml", cantidad=2, precio=12.0, confianza=0.95, crudo="AGUA 600ML 2"),
            Item(nombre="refresco cola", cantidad=6, precio=18.5, confianza=0.9, crudo="REFR COLA 6"),
            Item(nombre="galletas", cantidad=3, precio=9.0, confianza=0.55, crudo="GALL??? 3"),
        ], total=130.0, advertencias=["MOCK: datos de ejemplo"])


class RealVision:
    def __init__(self, weights: str):
        self.info = {"weights": weights, "sha256": _sha256(weights)}
        # TODO (rol A): cargar YOLO (.pt o .engine) y el OCR
        raise NotImplementedError

    def parse(self, imagen: bytes) -> ParsedTicket:
        raise NotImplementedError


def load(mock: bool):
    return MockVision() if mock else RealVision(os.environ["VISION_WEIGHTS"])
