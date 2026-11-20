"""
Extrae datos de un ticket usando el modelo YOLO (best.pt) + OCR.

Clases del modelo: renglon, total, fecha, tienda

Flujo:
  1. YOLO detecta las regiones (renglon / total / fecha / tienda).
  2. EasyOCR lee el texto de cada region (y de la imagen completa para
     detectar secciones VENTA / DEVOLUCION / CORTESIA y el folio).
  3. Se parsea el texto y se arma el JSON.

Instalacion:
    pip install ultralytics easyocr opencv-python

Uso:
    python ticket_extractor.py ticket.jpg --modelo best.pt --id-usuario 1
    python ticket_extractor.py ticket.jpg --margen 0.30 --stock-minimo 5 --debug
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------------
# Configuracion
# ----------------------------------------------------------------------------
CONF_MIN = 0.25
IMGSZ = 960  # mismo tamano con el que se entreno

CATEGORIAS = [  # (patron, categoria) -> ajusta a tu catalogo
    (r"COCA|PEPSI|SPRITE|FANTA|REFRESCO|SIDRAL", "Refrescos"),
    (r"AGUA|BONAFONT|CIEL", "Agua"),
    (r"YOG|DANONE|DANY|GRIEGO|BEBIBLE|BENEG|LECHE|CREMA|QUESO", "Lacteos"),
    (r"GALLETA|GAMESA|MARINELA|SABRITAS|BARCEL", "Botanas y galletas"),
]

SECCION_RE = re.compile(r"^\W*(CORTESIA|DEVOLUCION|VENTA)\W*$", re.I)
PRESENTACION_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(ML|LTS?|L|GR|G|KG)\b", re.I
)
FECHA_RE = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")
HORA_RE = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")
FOLIO_RE = re.compile(
    r"(?:folio|ticket|nota|no\.?)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{3,})", re.I
)
# SKU  P.U.  Cantidad  Subtotal   (el subtotal puede venir entre parentesis)
LINEA_NUM_RE = re.compile(
    r"(\d{4,})\s+\$?\s*(\d[\d.,]*)\s+(\d[\d.,]*)\s+\(?\s*-?\$?\s*(\d[\d.,]*)\s*\)?"
)


# ----------------------------------------------------------------------------
# Utilidades de OCR
# ----------------------------------------------------------------------------
_reader = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr

        _reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
    return _reader


def ocr_lineas(img, y_offset=0):
    """Devuelve [(y_centro, texto)] agrupando palabras en lineas."""
    import cv2

    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gris = cv2.resize(gris, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    res = get_reader().readtext(gris, detail=1, paragraph=False)

    palabras = []
    for caja, texto, _conf in res:
        ys = [p[1] for p in caja]
        xs = [p[0] for p in caja]
        palabras.append(
            {
                "y": sum(ys) / 4 / 2 + y_offset,
                "h": (max(ys) - min(ys)) / 2,
                "x": min(xs) / 2,
                "t": texto,
            }
        )
    palabras.sort(key=lambda p: p["y"])

    lineas, actual = [], []
    for p in palabras:
        if actual and abs(p["y"] - actual[-1]["y"]) > max(6, p["h"] * 0.6):
            lineas.append(actual)
            actual = []
        actual.append(p)
    if actual:
        lineas.append(actual)

    salida = []
    for grupo in lineas:
        grupo.sort(key=lambda p: p["x"])
        y = sum(p["y"] for p in grupo) / len(grupo)
        salida.append((y, " ".join(p["t"] for p in grupo)))
    return salida


# ----------------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------------
def a_numero(s):
    """'$1,234.50' / '(9.60)' / '9,60' -> float (None si no se puede)."""
    if s is None:
        return None
    s = s.replace("$", "").replace(" ", "")
    s = re.sub(r"[^\d.,]", "", s)
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parsear_fecha(texto):
    m = FECHA_RE.search(texto or "")
    if not m:
        return None
    d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if a < 100:
        a += 2000
    h = HORA_RE.search(texto)
    hh, mm, ss = (int(h.group(1)), int(h.group(2)), int(h.group(3) or 0)) if h else (0, 0, 0)
    try:
        return datetime(a, mes, d, hh, mm, ss).isoformat()
    except ValueError:
        try:  # quiza el formato es mes/dia/anio
            return datetime(a, d, mes, hh, mm, ss).isoformat()
        except ValueError:
            return None


def separar_presentacion(nombre):
    """'DANONE GRIEGO DURAZNO 435G' -> ('Danone Griego Durazno', '435 g')"""
    m = PRESENTACION_RE.search(nombre)
    if not m:
        return nombre.strip().title(), None
    cant = m.group(1).replace(",", ".")
    unidad = m.group(2).lower()
    unidad = {"gr": "g", "lt": "l", "lts": "l"}.get(unidad, unidad)
    if unidad == "l":
        unidad = "litros" if float(cant) != 1 else "litro"
    pres = f"{cant.rstrip('0').rstrip('.') if '.' in cant else cant} {unidad}"
    limpio = (nombre[: m.start()] + nombre[m.end():]).strip(" -")
    return limpio.title(), pres


def detectar_categoria(nombre):
    for patron, cat in CATEGORIAS:
        if re.search(patron, nombre, re.I):
            return cat
    return None


def parsear_renglon(lineas_texto, linea_previa=None):
    """
    lineas_texto: lista de strings OCR del recorte 'renglon'.
    linea_previa: texto de la linea inmediatamente superior (por si el
                  nombre quedo fuera del recuadro detectado).
    Devuelve dict o None.
    """
    texto = "\n".join(lineas_texto)
    m = LINEA_NUM_RE.search(texto.replace("\n", " "))
    if not m:
        return None
    sku, pu, qty, sub = m.groups()
    nombre = texto[: m.start()].replace("\n", " ").strip()
    if len(nombre) < 3 and linea_previa:
        nombre = linea_previa.strip()
    if len(nombre) < 3:
        return None
    # cantidad negativa/devolucion: el subtotal venia entre parentesis
    es_negativo = "(" in texto[m.start(): m.end()]
    return {
        "sku": sku,
        "nombre_raw": nombre,
        "precio_unitario": a_numero(pu),
        "cantidad": a_numero(qty),
        "subtotal": a_numero(sub),
        "negativo": es_negativo,
    }


# ----------------------------------------------------------------------------
# Pipeline principal
# ----------------------------------------------------------------------------
def extraer_ticket(
    ruta_imagen,
    modelo="best.pt",
    id_usuario=1,
    stock_minimo=5,
    margen=None,
    incluir_devoluciones=False,
    debug=False,
):
    import cv2
    from ultralytics import YOLO

    img = cv2.imread(str(ruta_imagen))
    if img is None:
        raise FileNotFoundError(f"No se pudo abrir la imagen: {ruta_imagen}")

    yolo = YOLO(modelo)
    pred = yolo.predict(img, imgsz=IMGSZ, conf=CONF_MIN, verbose=False)[0]
    nombres = pred.names

    dets = {"renglon": [], "total": [], "fecha": [], "tienda": []}
    for b in pred.boxes:
        clase = nombres[int(b.cls)]
        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
        dets[clase].append({"box": (x1, y1, x2, y2), "conf": float(b.conf)})

    def mejor(clase):
        return max(dets[clase], key=lambda d: d["conf"]) if dets[clase] else None

    def leer(det, pad=4):
        x1, y1, x2, y2 = det["box"]
        h, w = img.shape[:2]
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        return ocr_lineas(img[y1:y2, x1:x2], y_offset=y1)

    # --- OCR de la imagen completa (secciones, folio, texto de apoyo) -------
    completo = ocr_lineas(img)
    texto_completo = "\n".join(t for _, t in completo)
    secciones = [(y, SECCION_RE.match(t).group(1).upper())
                 for y, t in completo if SECCION_RE.match(t)]

    def seccion_de(y):
        actual = "VENTA"
        for ys, nombre in secciones:
            if ys <= y:
                actual = nombre
        return actual

    # --- campos simples -------------------------------------------------------
    d_tienda, d_fecha, d_total = mejor("tienda"), mejor("fecha"), mejor("total")

    proveedor = None
    if d_tienda:
        proveedor = " ".join(t for _, t in leer(d_tienda)).strip().title() or None

    fecha = None
    if d_fecha:
        fecha = parsear_fecha(" ".join(t for _, t in leer(d_fecha)))
    if not fecha:
        fecha = parsear_fecha(texto_completo)

    total = None
    if d_total:
        nums = re.findall(r"\d[\d.,]*", " ".join(t for _, t in leer(d_total)))
        if nums:
            total = a_numero(nums[-1])

    m = FOLIO_RE.search(texto_completo)
    folio = m.group(1) if m else None

    # --- renglones ------------------------------------------------------------
    renglones = []
    for d in sorted(dets["renglon"], key=lambda d: d["box"][1]):
        x1, y1, x2, y2 = d["box"]
        lineas = leer(d)
        previa = None
        candidatas = [t for y, t in completo if y < y1 and y1 - y < 40]
        if candidatas:
            previa = candidatas[-1]
        r = parsear_renglon([t for _, t in lineas], previa)
        if r:
            r["seccion"] = seccion_de((y1 + y2) / 2)
            renglones.append(r)

    productos, devoluciones = [], []
    for r in renglones:
        if r["seccion"] == "CORTESIA":
            continue
        if r["seccion"] == "DEVOLUCION" and not incluir_devoluciones:
            devoluciones.append(r)
            continue
        nombre, presentacion = separar_presentacion(r["nombre_raw"])
        pu = r["precio_unitario"]
        productos.append(
            {
                "nombre": nombre,
                "presentacion": presentacion,
                "codigo_barras": None,  # el ticket solo trae SKU interno
                "unidad": "pieza",
                "cantidad": r["cantidad"],
                "precio_unitario": pu,
                "precio_venta": round(pu * (1 + margen), 2) if (margen and pu) else None,
                "stock_minimo": stock_minimo,
                "categoria": detectar_categoria(r["nombre_raw"]),
            }
        )

    # --- respaldos ------------------------------------------------------------
    if not proveedor and productos:
        proveedor = productos[0]["nombre"].split()[0]
    if total is None:
        ventas = sum(r["subtotal"] or 0 for r in renglones if r["seccion"] == "VENTA")
        total = round(ventas, 2) or None

    resultado = {
        "id_usuario": id_usuario,
        "ticket": {
            "proveedor": proveedor,
            "folio": folio,
            "fecha_compra": fecha,
            "total": total,
            "ruta_imagen": str(ruta_imagen),
            "productos": productos,
        },
    }
    if debug:
        resultado["_debug"] = {
            "detecciones": {k: len(v) for k, v in dets.items()},
            "secciones": secciones,
            "renglones": renglones,
            "devoluciones_excluidas": devoluciones,
        }
        anotada = pred.plot()
        cv2.imwrite(str(Path(ruta_imagen).with_suffix(".det.jpg")), anotada)
    return resultado


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("imagen", nargs="?",
                default=r"D:\Nvidia-Hacakaton-026--aplicaion-para-el-dia-a-dia-en-tienda-\backend\WhatsApp Image 2026-11-19 at 2.57.35 PM.jpeg")
    ap.add_argument("--modelo",
                default=r"D:\Nvidia-Hacakaton-026--aplicaion-para-el-dia-a-dia-en-tienda-\backend\weights\best.pt")
    ap.add_argument("--id-usuario", type=int, default=1)
    ap.add_argument("--stock-minimo", type=int, default=5)
    ap.add_argument("--margen", type=float, default=None,
                    help="margen para calcular precio_venta (0.30 = +30%%)")
    ap.add_argument("--incluir-devoluciones", action="store_true")
    ap.add_argument("--debug", action="store_true",
                    help="agrega _debug al JSON y guarda <imagen>.det.jpg con las cajas")
    a = ap.parse_args()

    out = extraer_ticket(
        a.imagen, a.modelo, a.id_usuario, a.stock_minimo, a.margen,
        a.incluir_devoluciones, a.debug,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()