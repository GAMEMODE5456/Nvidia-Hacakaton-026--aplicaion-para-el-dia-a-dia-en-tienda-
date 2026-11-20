
"""
Ruta FastAPI para escanear tickets y guardarlos automáticamente.

Proceso:
1. Recibir fotografía.
2. Ejecutar PaddleOCR.
3. Interpretar el ticket.
4. Guardar en MariaDB.
5. Devolver resultado al frontend.
"""

import re
import statistics
import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile
)

from fastapi.concurrency import run_in_threadpool

from parser_tickets import parsear_ticket
from services.crear_tickets import crear_ticket


router = APIRouter(
    prefix="/ocr",
    tags=["OCR"]
)

CARPETA_TICKETS = (
    Path(__file__).resolve().parent / "tickets"
)

CARPETA_TICKETS.mkdir(
    parents=True,
    exist_ok=True
)

MAX_BYTES = 12 * 1024 * 1024

EXTENSIONES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp"
}

_ocr = None


# =============================================
# 1. INICIALIZAR PADDLEOCR
# =============================================

def obtener_ocr():

    global _ocr

    if _ocr is None:

        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(
            lang="es",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )

    return _ocr


# =============================================
# 2. AGRUPAR TEXTO EN LÍNEAS
# =============================================

def _agrupar_en_lineas(textos, cajas):

    if not cajas or len(cajas) != len(textos):

        return [
            t for t in textos
            if t and t.strip()
        ]

    items = []

    for t, c in zip(textos, cajas):

        if not t or not t.strip():
            continue

        x1, y1, x2, y2 = [
            float(v) for v in c
        ]

        items.append({
            "t": t.strip(),
            "x": x1,
            "y": (y1 + y2) / 2,
            "h": max(y2 - y1, 1)
        })

    if not items:
        return []

    alto = statistics.median(
        i["h"] for i in items
    )

    items.sort(
        key=lambda i: i["y"]
    )

    filas = []
    actual = [items[0]]

    for it in items[1:]:

        ref = sum(
            i["y"] for i in actual
        ) / len(actual)

        if abs(it["y"] - ref) <= alto * 0.6:

            actual.append(it)

        else:

            filas.append(actual)
            actual = [it]

    filas.append(actual)

    return [
        " ".join(
            i["t"]
            for i in sorted(f, key=lambda i: i["x"])
        )
        for f in filas
    ]


# =============================================
# 3. LEER FOTOGRAFÍA CON OCR
# =============================================

def leer_lineas(ruta_imagen: str):

    ocr = obtener_ocr()

    resultado = ocr.predict(ruta_imagen)

    lineas = []

    for pagina in resultado:

        datos = (
            pagina.json["res"]
            if hasattr(pagina, "json")
            else pagina
        )

        textos = list(
            datos.get("rec_texts", [])
        )

        cajas = datos.get("rec_boxes")

        cajas = (
            [list(c) for c in cajas]
            if cajas is not None and len(cajas)
            else []
        )

        lineas.extend(
            _agrupar_en_lineas(textos, cajas)
        )

    return lineas


# =============================================
# 4. ENDPOINT PARA LEER Y GUARDAR TICKET
# =============================================

@router.post("/leer-ticket")
async def leer_ticket(

    imagen: UploadFile = File(...),

    id_usuario: int = Query(1)

):

    # -----------------------------------------
    # VALIDAR IMAGEN
    # -----------------------------------------

    ext = Path(
        imagen.filename or ""
    ).suffix.lower()

    if ext not in EXTENSIONES:

        raise HTTPException(
            status_code=400,
            detail="Sube una imagen JPG, PNG o WEBP."
        )

    contenido = await imagen.read()

    if not contenido:

        raise HTTPException(
            status_code=400,
            detail="La imagen está vacía."
        )

    if len(contenido) > MAX_BYTES:

        raise HTTPException(
            status_code=413,
            detail="La imagen pesa más de 12 MB."
        )

    # -----------------------------------------
    # GUARDAR FOTOGRAFÍA
    # -----------------------------------------

    nombre = f"{uuid.uuid4().hex}{ext}"

    ruta = CARPETA_TICKETS / nombre

    ruta.write_bytes(contenido)

    ruta_relativa = f"tickets/{nombre}"

    try:

        # -------------------------------------
        # PASO 1: EJECUTAR OCR
        # -------------------------------------

        lineas = await run_in_threadpool(
            leer_lineas,
            str(ruta)
        )

        if not lineas:

            raise HTTPException(
                status_code=422,
                detail="No se detectó texto en el ticket."
            )

        # -------------------------------------
        # PASO 2: INTERPRETAR TICKET
        # -------------------------------------

        ticket, advertencias = parsear_ticket(
            lineas,
            ruta_relativa
        )

        # -------------------------------------
        # PASO 3: AGREGAR RUTA DE IMAGEN
        # -------------------------------------

        ticket["ruta_imagen"] = ruta_relativa

        # -------------------------------------
        # PASO 4: GUARDAR EN MARIADB
        # -------------------------------------

        registro = await run_in_threadpool(
            crear_ticket,
            ticket,
            id_usuario
        )

        # -------------------------------------
        # PASO 5: RESPONDER AL FRONTEND
        # -------------------------------------

        return {

            "id_usuario": id_usuario,

            "id_ticket": registro["id_ticket"],

            "id_proveedor": registro["id_proveedor"],

            "guardado": True,

            "mensaje": registro["mensaje"],

            "ticket": ticket,

            "registro": registro,

            "advertencias": advertencias,

            "texto_leido": lineas

        }

    except HTTPException:

        raise

    except ValueError as e:

        print("Error de validación:", e)

        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except ConnectionError as e:

        print("Error de conexión MariaDB:", e)

        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar con MariaDB."
        )

    except Exception as e:

        print("Error al procesar ticket:", e)

        raise HTTPException(
            status_code=500,
            detail="No se pudo procesar o guardar el ticket."
        )
