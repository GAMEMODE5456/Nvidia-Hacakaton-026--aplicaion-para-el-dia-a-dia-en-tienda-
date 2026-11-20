from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductoTicket(BaseModel):

    nombre: str
    presentacion: str

    codigo_barras: Optional[str] = None

    unidad: str = "pieza"

    cantidad: float = Field(gt=0)

    # Precio que se pagó al proveedor
    precio_unitario: float = Field(ge=0)

    # Precio que se cobrará al cliente
    precio_venta: Optional[float] = Field(default=None, ge=0)

    stock_minimo: float = Field(default=5, ge=0)

    categoria: str = "Sin categoría"


class DatosTicket(BaseModel):

    proveedor: str

    folio: Optional[str] = None

    fecha_compra: Optional[datetime] = None

    total: float = Field(ge=0)

    ruta_imagen: Optional[str] = None

    productos: list[ProductoTicket] = Field(min_length=1)


class CrearTicketRequest(BaseModel):

    id_usuario: int

    ticket: DatosTicket