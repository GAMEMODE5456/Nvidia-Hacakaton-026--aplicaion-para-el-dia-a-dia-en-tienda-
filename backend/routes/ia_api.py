from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile
import os
import json

from ticket_extractor import extraer_ticket

router = APIRouter(prefix="/ia", tags=["Inteligencia Artificial"])

# Ruta del modelo reentrenado
BASE_DIR = Path(__file__).resolve().parent.parent
MODELO = BASE_DIR / "weights" / "best.pt"


@router.post("/leer-ticket")
async def leer_ticket(
    imagen: UploadFile = File(...),
    id_usuario: int = 1
):
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen"
        )

    if not MODELO.exists():
        raise HTTPException(
            status_code=500,
            detail=f"No se encontró el modelo: {MODELO}"
        )

    extension = Path(imagen.filename or "ticket.jpg").suffix or ".jpg"
    ruta_temporal = None

    try:
        contenido = await imagen.read()

        if not contenido:
            raise HTTPException(
                status_code=400,
                detail="La imagen está vacía"
            )

        # Guardar temporalmente la fotografía
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as archivo:
            archivo.write(contenido)
            ruta_temporal = archivo.name

        # Ejecutar YOLO + EasyOCR
        resultado = extraer_ticket(
            ruta_imagen=ruta_temporal,
            modelo=str(MODELO),
            id_usuario=id_usuario
        )

        print("\n========== RESULTADO DEL MODELO ==========")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
        print("==========================================\n")

        return {
            "success": True,
            "mensaje": "Ticket procesado correctamente",
            "resultado": resultado
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el ticket: {str(error)}"
        )

    finally:
        if ruta_temporal and os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)