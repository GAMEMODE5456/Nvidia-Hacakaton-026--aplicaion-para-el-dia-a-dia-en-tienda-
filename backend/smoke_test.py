import os
os.environ["DB_PATH"] = "/tmp/t.db"; os.environ["MOCK_MODELS"] = "1"
if os.path.exists("/tmp/t.db"): os.remove("/tmp/t.db")
from fastapi.testclient import TestClient
from backend.main import app
with TestClient(app) as c:
    print(c.get("/health").json())
    t = c.post("/ticket/parse", files={"file": ("a.jpg", b"x")}).json()
    r = c.post("/inventory/bulk_add", json={"items": t["items"]}).json(); print(r)
    for txt in ["quiero escanear un ticket", "ver mi inventario", "regresar al menu",
                "como escaneo una nota", "ayuda", "cual es la capital de francia", "hm"]:
        print(txt, "->", c.post("/assistant/interpret", json={"texto": txt}).json())
    print(c.post(f"/inventory/undo/{r['lote']}").json())
    print(c.get("/inventory").json())
