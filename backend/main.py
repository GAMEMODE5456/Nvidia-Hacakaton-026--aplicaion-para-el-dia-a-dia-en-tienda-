from fastapi import FastAPI
from routes.tickets import router as tickets_router
from routes.ia_api import router as ia_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Miscelánea IA",
    description="API de gestión de tickets e inventario",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.include_router(tickets_router)
app.include_router(ia_router)


@app.get("/")
def inicio():
    return {
        "mensaje": "API Miscelánea IA funcionando"
    }