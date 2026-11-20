
"""
parser_tickets.py

Convierte el texto reconocido por PaddleOCR en la estructura
JSON que utiliza el proyecto.

No depende de FastAPI, YOLO ni EasyOCR.

Uso:
    python parser_tickets.py
"""

import re
import json
from datetime import datetime


# ==========================================================
# EXPRESIONES REGULARES
# ==========================================================

PRECIO = re.compile(
    r"(?<![\d.,])\$?\s*(\d{1,3}(?:,\d{3})+\.\d{2}|\d+[.,]\d{2})(?!\d)"
)

PREFIJO_CANT = re.compile(
    r"^\s*(\d{1,3}(?:[.,]\d+)?)\s*(?:[xX*]\s*|\s+)(?=\D)"
)

CANT_X = re.compile(
    r"(\d{1,3}(?:[.,]\d+)?)\s*[xX*]\s*(?=\$?\d)"
)

BARRAS = re.compile(r"\b\d{8,14}\b")

PRESENT = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(ml|lts?|litros?|l|gr?s?|kg|oz|pzas?|piezas?)\b",
    re.IGNORECASE
)

FOLIO = re.compile(
    r"\b(?:folio|ticket|tkt|nota|factura)\s*"
    r"(?:no\.?|num\.?|#)?\s*[:#.\-]?\s*"
    r"([A-Z0-9-]{3,})\b",
    re.IGNORECASE
)

FECHA_DMA = re.compile(
    r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})(?!\d)"
)

FECHA_AMD = re.compile(
    r"(?<!\d)(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})(?!\d)"
)

HORA = re.compile(
    r"(?<!\d)(\d{1,2}):(\d{2})(?::(\d{2}))?(?!\d)"
)

LINEA_TOTAL = re.compile(r"\btotal\b", re.IGNORECASE)

NO_PRODUCTO = re.compile(
    r"\b(subtotal|total|iva|efectivo|cambio|pago|tarjeta|"
    r"gracias|folio|fecha|rfc|tel|cajero|articulos|artículos|"
    r"descuento|visa|mastercard|redondeo|recibido|ticket|"
    r"hora|sucursal|direccion|dirección|factura)\b",
    re.IGNORECASE
)

NO_PROVEEDOR = re.compile(
    r"\b(ticket|folio|fecha|rfc|tel|tels|calle|col|cp|www|http|"
    r"av|avenida|sucursal|hora|nota|venta|cliente)\b",
    re.IGNORECASE
)


# ==========================================================
# UTILIDADES
# ==========================================================

def a_numero(texto: str) -> float:
    """Convierte cantidades monetarias a número decimal."""

    texto = texto.replace(" ", "").replace("$", "")

    if re.fullmatch(r"\d+,\d{2}", texto):
        texto = texto.replace(",", ".")
    else:
        texto = texto.replace(",", "")

    return round(float(texto), 2)


def _a_cantidad(texto: str) -> float:
    """Convierte cantidades enteras o decimales."""

    return float(texto.replace(",", "."))


def _letras(texto: str) -> int:
    return len(
        re.findall(
            r"[A-Za-zÁÉÍÓÚÑáéíóúñ]",
            texto
        )
    )


def _normalizar_presentacion(match: re.Match) -> str:

    numero = match.group(1).replace(",", ".")
    unidad = match.group(2).lower()

    if unidad in ("l", "lt", "lts", "litro", "litros"):
        unidad = "litro" if float(numero) == 1 else "litros"

    elif unidad.startswith("g"):
        unidad = "g"

    elif unidad.startswith("p"):
        unidad = "pzas"

    return f"{numero} {unidad}"


# ==========================================================
# DATOS DEL ENCABEZADO
# ==========================================================

def _buscar_proveedor(lineas):

    for linea in lineas[:8]:

        texto = linea.strip()

        if _letras(texto) < 3:
            continue

        if NO_PROVEEDOR.search(texto):
            continue

        if _letras(texto) < len(texto) * 0.5:
            continue

        return texto.title() if texto.isupper() else texto

    return None


def _buscar_folio(lineas):

    for linea in lineas:

        match = FOLIO.search(linea)

        if match:
            return match.group(1).upper()

    return None


def _buscar_fecha(lineas):

    fecha = None
    hora = (0, 0, 0)

    for linea in lineas:

        if fecha is None:

            match = FECHA_AMD.search(linea)

            if match:
                anio = int(match.group(1))
                mes = int(match.group(2))
                dia = int(match.group(3))

            else:

                match = FECHA_DMA.search(linea)

                if not match:
                    continue

                dia = int(match.group(1))
                mes = int(match.group(2))
                anio = int(match.group(3))

                if anio < 100:
                    anio += 2000

            try:
                fecha = datetime(anio, mes, dia)

            except ValueError:
                continue

            match_hora = HORA.search(linea)

            if match_hora:
                hora = (
                    int(match_hora.group(1)),
                    int(match_hora.group(2)),
                    int(match_hora.group(3) or 0)
                )

        elif hora == (0, 0, 0):

            match_hora = HORA.search(linea)

            if match_hora:
                hora = (
                    int(match_hora.group(1)),
                    int(match_hora.group(2)),
                    int(match_hora.group(3) or 0)
                )

    if fecha is None:
        return None

    try:

        fecha = fecha.replace(
            hour=hora[0],
            minute=hora[1],
            second=hora[2]
        )

    except ValueError:
        pass

    return fecha.strftime("%Y-%m-%dT%H:%M:%S")


def _buscar_total(lineas):

    for linea in lineas:

        if LINEA_TOTAL.search(linea):

            precios = [
                a_numero(match.group(1))
                for match in PRECIO.finditer(linea)
            ]

            if precios:
                return precios[-1]

    return None


# ==========================================================
# IDENTIFICACIÓN DE PRODUCTOS
# ==========================================================

def _parsear_producto(linea: str):

    precios = [
        a_numero(match.group(1))
        for match in PRECIO.finditer(linea)
    ]

    if not precios:
        return None

    if NO_PRODUCTO.search(linea):
        return None

    texto = PRECIO.sub(" ", linea)

    cantidad = None

    # Cantidad al inicio: 2 COCA COLA
    match = PREFIJO_CANT.match(texto)

    if match:

        cantidad = _a_cantidad(match.group(1))
        texto = texto[match.end():]

    else:

        # Cantidad en formato: COCA COLA 2 X 15.00
        match = CANT_X.search(texto)

        if match:

            cantidad = _a_cantidad(match.group(1))

            texto = (
                texto[:match.start()]
                + " "
                + texto[match.end():]
            )

    # Código de barras
    codigo = None

    match = BARRAS.search(texto)

    if match:

        codigo = match.group(0)
        texto = texto.replace(codigo, " ")

    # Presentación del producto
    presentacion = None

    match = PRESENT.search(texto)

    if match:

        presentacion = _normalizar_presentacion(match)

        texto = (
            texto[:match.start()]
            + " "
            + texto[match.end():]
        )

    # Limpiar nombre
    nombre = re.sub(r"[$*|_]+", " ", texto)

    nombre = re.sub(
        r"(?<!\S)[xX](?!\S)",
        " ",
        nombre
    )

    nombre = re.sub(r"\s+", " ", nombre)

    nombre = re.sub(
        r"^[\s\-.:,]+|[\s\-.:,]+$",
        "",
        nombre
    )

    if _letras(nombre) < 2:
        return None

    if nombre.isupper():
        nombre = nombre.title()

    # Importe y precio unitario
    importe = precios[-1]

    unitario = precios[0] if len(precios) > 1 else None

    if cantidad is None:

        cantidad = 1

        if unitario is not None and unitario > 0:

            ratio = importe / unitario

            if ratio >= 1 and abs(ratio - round(ratio)) < 0.02:
                cantidad = round(ratio)

    if cantidad <= 0:
        return None

    if unitario is None:
        unitario = round(importe / cantidad, 2)

    if float(cantidad).is_integer():
        cantidad = int(cantidad)

    return {
        "nombre": nombre,
        "presentacion": presentacion,
        "codigo_barras": codigo,
        "unidad": "pieza" if isinstance(cantidad, int) else "kg",
        "cantidad": cantidad,
        "precio_unitario": round(unitario, 2),
        "precio_venta": None,
        "stock_minimo": None,
        "categoria": None,
        "_importe": round(importe, 2)
    }


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================

def parsear_ticket(lineas, ruta_imagen=None):

    """
    Recibe las líneas reconocidas por PaddleOCR.

    Devuelve:
        ticket: diccionario con los datos del ticket.
        advertencias: lista de observaciones.
    """

    if not isinstance(lineas, (list, tuple)):
        raise TypeError("Las líneas del OCR deben ser una lista.")

    lineas = [
        str(linea).strip()
        for linea in lineas
        if linea is not None and str(linea).strip()
    ]

    advertencias = []

    # ------------------------------------------------------
    # PRODUCTOS
    # ------------------------------------------------------

    productos = []

    for linea in lineas:

        producto = _parsear_producto(linea)

        if producto:
            productos.append(producto)

    suma = round(
        sum(producto["_importe"] for producto in productos),
        2
    )

    # ------------------------------------------------------
    # TOTAL
    # ------------------------------------------------------

    total = _buscar_total(lineas)

    if total is None and productos:

        total = suma

        advertencias.append(
            "No se encontró la línea TOTAL; "
            "se sumaron los importes de los productos."
        )

    elif total is not None and productos:

        if abs(total - suma) > 0.05:

            advertencias.append(
                f"La suma de productos ({suma:.2f}) "
                f"no coincide con el total ({total:.2f}). "
                "Revisa los productos."
            )

    # Eliminar campo interno
    for producto in productos:
        producto.pop("_importe", None)

    # ------------------------------------------------------
    # ENCABEZADO
    # ------------------------------------------------------

    proveedor = _buscar_proveedor(lineas)

    folio = _buscar_folio(lineas)

    fecha = _buscar_fecha(lineas)

    if not proveedor:
        advertencias.append("No se pudo leer el proveedor.")

    if not folio:
        advertencias.append("No se pudo leer el folio.")

    if not fecha:
        advertencias.append("No se pudo leer la fecha.")

    if not productos:
        advertencias.append("No se detectaron productos.")

    # ------------------------------------------------------
    # RESULTADO
    # ------------------------------------------------------

    ticket = {
        "proveedor": proveedor,
        "folio": folio,
        "fecha_compra": fecha,
        "total": total,
        "ruta_imagen": ruta_imagen,
        "productos": productos
    }

    return ticket, advertencias


# ==========================================================
# PRUEBA INDEPENDIENTE
# ==========================================================

if __name__ == "__main__":

    ejemplo = [
        "MAYOREO LA CAMPESINA",
        "RFC XAXX010101000",
        "Av. Juarez 123",
        "FOLIO: 171733",
        "FECHA 03-05-2026 10:15:32",
        "CANT DESCRIPCION IMPORTE",
        "2 COCA COLA 600ML 15.00 30.00",
        "1 SABRITAS ORIGINAL 45g 86.80",
        "SUBTOTAL 116.80",
        "TOTAL $116.80",
        "EFECTIVO 200.00",
        "CAMBIO 83.20",
        "GRACIAS POR SU COMPRA"
    ]

    ticket, advertencias = parsear_ticket(
        ejemplo,
        "tickets/ejemplo.jpg"
    )

    resultado = {
        "id_usuario": 1,
        "ticket": ticket,
        "advertencias": advertencias
    }

    print("\n========== RESULTADO DEL PARSER ==========")

    print(
        json.dumps(
            resultado,
            indent=4,
            ensure_ascii=False
        )
    )

    print("==========================================")
