"""CONTRATOS. No cambiar sin avisar al equipo."""
from typing import Literal, Optional
from pydantic import BaseModel


class Item(BaseModel):
    nombre: str
    cantidad: float = 1
    precio: Optional[float] = None
    confianza: float = 1.0      # <0.7 -> el frontend lo marca "Revise este"
    crudo: str = ""             # texto original leido del ticket


class ParsedTicket(BaseModel):
    items: list[Item]
    total: Optional[float] = None
    fecha: Optional[str] = None
    advertencias: list[str] = []


Destino = Literal["inicio", "escanear_ticket", "inventario"]


class Accion(BaseModel):
    """Salida del asistente de navegacion. NO modifica datos."""
    accion: Literal["navegar", "ayuda", "aclarar", "fuera_de_alcance"]
    destino: Optional[Destino] = None   # pantalla a abrir (navegar / ayuda)
    mensaje: str = ""                   # texto corto para mostrar Y leer en voz alta


class BulkAddRequest(BaseModel):
    items: list[Item]           # ya revisados/corregidos por el usuario


class InterpretRequest(BaseModel):
    texto: str


class Resultado(BaseModel):
    ok: bool
    mensaje: str                # texto para mostrar Y leer en voz alta
    lote: Optional[int] = None  # id para "Deshacer"
