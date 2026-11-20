import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .schemas import (Accion, BulkAddRequest, InterpretRequest, ParsedTicket, Resultado)
from .services import actions, llm, normalizer, vision


@asynccontextmanager
async def lifespan(app: FastAPI):
    mock = os.getenv("MOCK_MODELS", "1") == "1"
    db.init()
    app.state.vision = vision.load(mock)
    app.state.llm = llm.load(mock)
    app.state.mock = mock
    yield


app = FastAPI(title="Don Nacho Digital API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"version": os.getenv("APP_VERSION", "dev"), "mock_models": app.state.mock,
            "vision": app.state.vision.info, "llm": app.state.llm.info}


@app.post("/ticket/parse", response_model=ParsedTicket)
async def ticket_parse(file: UploadFile = File(...)):
    data = await file.read()
    try:
        t = app.state.vision.parse(data)
    except Exception as e:
        raise HTTPException(422, f"No pude leer bien el ticket. Intente con más luz. ({e})")
    t.items = normalizer.normalizar(t.items)
    return t


@app.post("/inventory/bulk_add", response_model=Resultado)
def bulk_add(req: BulkAddRequest):
    return actions.bulk_add(req.items)


@app.post("/inventory/undo/{lote}", response_model=Resultado)
def undo(lote: int):
    return actions.undo(lote)


@app.get("/inventory")
def inventory():
    with db.conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT nombre, cantidad, precio FROM productos ORDER BY nombre")]


@app.post("/assistant/interpret", response_model=Accion)
def interpret(req: InterpretRequest):
    try:
        return app.state.llm.interpret(req.texto)   # solo navegacion; no escribe datos
    except Exception:
        raise HTTPException(503, "El asistente no está disponible. Intente de nuevo.")


@app.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    raise HTTPException(501, "ASR pendiente (opcional). Use texto o Web Speech API.")
