
"""
Ruta FastAPI para escanear tickets y guardarlos automáticamente.

Proceso:
1. Recibir fotografía.
2. Ejecutar PaddleOCR.
3. Interpretar el ticket con parser_tickets.py.
4. Guardar ticket y productos en MariaDB.
5. Devolver resultado al frontend.
"""

import uuid
from pathlib import Path
from threading import Lock

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Query
)

from fastapi.concurrency import run_in_threadpool

from parser_tickets import parsear_ticket
from services.crear_tickets import crear_ticket


router = APIRouter(
    prefix="/ia",
    tags=["Inteligencia Artificial"]
)


# =============================================
# CONFIGURACIÓN
# =============================================

BASE_DIR = Path(__file__).resolve().parent.parent

CARPETA_TICKETS = BASE_DIR / "tickets"

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
_ocr_lock = Lock()


# =============================================
# 1. INICIALIZAR PADDLEOCR
# =============================================

def obtener_ocr():

    global _ocr

    if _ocr is None:

        with _ocr_lock:

            if _ocr is None:

                from paddleocr import PaddleOCR

                print("Inicializando PaddleOCR...")

                _ocr = PaddleOCR(
                    lang="es",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    enable_mkldnn=False
                )

                print("PaddleOCR inicializado correctamente.")

    return _ocr


# =============================================
# 2. AGRUPAR TEXTO EN LÍNEAS
# =============================================

def agrupar_en_lineas(textos, cajas):

    if not cajas or len(cajas) != len(textos):

        return [
            texto.strip()
            for texto in textos
            if texto and texto.strip()
        ]

    elementos = []

    for texto, caja in zip(textos, cajas):

        if not texto or not texto.strip():
            continue

        x1, y1, x2, y2 = [
            float(valor) for valor in caja
        ]

        elementos.append({
            "texto": texto.strip(),
            "x": x1,
            "y": (y1 + y2) / 2,
            "alto": max(y2 - y1, 1)
        })

    if not elementos:
        return []

    alto_mediano = sorted(
        elemento["alto"] for elemento in elementos
    )[len(elementos) // 2]

    elementos.sort(
        key=lambda elemento: elemento["y"]
    )

    filas = []
    fila_actual = [elementos[0]]

    for elemento in elementos[1:]:

        referencia = sum(
            item["y"] for item in fila_actual
        ) / len(fila_actual)

        if abs(elemento["y"] - referencia) <= alto_mediano * 0.6:

            fila_actual.append(elemento)

        else:

            filas.append(fila_actual)
            fila_actual = [elemento]

    filas.append(fila_actual)

    return [
        " ".join(
            item["texto"]
            for item in sorted(
                fila,
                key=lambda item: item["x"]
            )
        )
        for fila in filas
    ]


# =============================================
# 3. EXTRAER TEXTO CON PADDLEOCR
# =============================================

def leer_lineas(ruta_imagen: str):

    ocr = obtener_ocr()

    resultado = ocr.predict(ruta_imagen)

    lineas = []

    for pagina in resultado:

        # Obtener los datos del resultado
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
            [list(caja) for caja in cajas]
            if cajas is not None and len(cajas)
            else []
        )

        lineas.extend(
            agrupar_en_lineas(textos, cajas)
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

    ruta_imagen = None
    guardado_correctamente = False

    try:

        # -------------------------------------
        # VALIDAR IMAGEN
        # -------------------------------------

        extension = Path(
            imagen.filename or ""
        ).suffix.lower()

        if extension not in EXTENSIONES:

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
                detail="La imagen supera el límite de 12 MB."
            )

        # -------------------------------------
        # GUARDAR FOTOGRAFÍA
        # -------------------------------------

        nombre = f"{uuid.uuid4().hex}{extension}"

        ruta_imagen = CARPETA_TICKETS / nombre

        ruta_imagen.write_bytes(contenido)

        ruta_relativa = f"tickets/{nombre}"

        # -------------------------------------
        # PASO 1: EJECUTAR PADDLEOCR
        # -------------------------------------

        print("Procesando imagen con PaddleOCR...")

        lineas = await run_in_threadpool(
            leer_lineas,
            str(ruta_imagen)
        )

        if not lineas:

            raise HTTPException(
                status_code=422,
                detail="No se detectó texto en el ticket."
            )

        print("Texto detectado:", lineas)

        # -------------------------------------
        # PASO 2: INTERPRETAR EL TICKET
        # -------------------------------------

        ticket, advertencias = parsear_ticket(
            lineas,
            ruta_relativa
        )

        ticket["ruta_imagen"] = ruta_relativa

        # -------------------------------------
        # PASO 3: GUARDAR EN MARIADB
        # -------------------------------------

        print("Guardando ticket en MariaDB...")

        registro = await run_in_threadpool(
            crear_ticket,
            ticket,
            id_usuario
        )

        guardado_correctamente = True

        print("Ticket guardado correctamente.")

        # -------------------------------------
        # PASO 4: RESPUESTA AL FRONTEND
        # -------------------------------------

        return {
            "success": True,
            "guardado": True,
            "mensaje": "Ticket procesado y guardado correctamente",
            "id_usuario": id_usuario,
            "id_ticket": registro["id_ticket"],
            "id_proveedor": registro["id_proveedor"],
            "ticket": ticket,
            "registro": registro,
            "advertencias": advertencias,
            "texto_leido": lineas
        }

    except HTTPException:
        raise

    except ValueError as error:

        print("Error de validación:", repr(error))

        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except ConnectionError as error:

        print("Error de conexión MariaDB:", repr(error))

        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar con MariaDB."
        )

    except Exception as error:

        print("Error al procesar ticket:", repr(error))

        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el ticket: {str(error)}"
        )

    finally:

        # Si no se pudo guardar el ticket,
        # eliminar la fotografía para evitar archivos huérfanos.

        if ruta_imagen is not None and not guardado_correctamente:

            try:

                if ruta_imagen.exists():
                    ruta_imagen.unlink()

            except OSError as error:

                print(
                    "No se pudo eliminar la imagen:",
                    repr(error)
                )

        await imagen.close()
