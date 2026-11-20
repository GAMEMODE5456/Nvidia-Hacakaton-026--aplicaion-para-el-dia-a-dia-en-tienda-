from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------- App ----------
app = FastAPI(title="Miscelánea IA", version="1.0.0")

# ---------- CORS (por si abres la página desde otra dirección) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Frontend ----------
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"

# Evita que el navegador guarde una versión vieja (el JSON de bienvenida)
NO_CACHE = {"Cache-Control": "no-store, max-age=0"}


@app.get("/", include_in_schema=False)
def inicio():
    if not INDEX_FILE.exists():
        return JSONResponse(
            status_code=500,
            content={"detail": f"No se encontró el frontend en: {INDEX_FILE}"},
        )
    return FileResponse(INDEX_FILE, media_type="text/html", headers=NO_CACHE)


@app.get("/api", tags=["Sistema"])
def api_info():
    return {
        "mensaje": "Bienvenido a la API de Miscelánea IA",
        "version": "1.0.0",
        "endpoints": {
            "tickets": "/tickets/",
            "ia": "/ia/",
            "usuarios": "/usuarios/",
            "login": "/login/",
        },
    }


@app.get("/salud", tags=["Sistema"])
def salud():
    return {"estado": "ok"}


# Archivos extra del frontend, solo si existen (no tapan la API)
for carpeta in ("css", "js", "assets"):
    ruta = FRONTEND_DIR / carpeta
    if ruta.is_dir():
        app.mount(f"/{carpeta}", StaticFiles(directory=ruta), name=carpeta)

# ---------- A PARTIR DE AQUÍ VA TU CÓDIGO ACTUAL ----------
# Tus include_router(...) y tus @app.post("/login/"), "/usuarios/",
# "/tickets/", "/ia/leer-ticket", etc. se quedan igual.
# BORRA tu antiguo @app.get("/") de bienvenida: ya lo reemplaza /api.