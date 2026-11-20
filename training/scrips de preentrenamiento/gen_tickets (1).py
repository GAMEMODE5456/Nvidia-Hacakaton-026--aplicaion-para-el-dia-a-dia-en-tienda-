#!/usr/bin/env python3
"""
Generador de tickets sintéticos (captura "Vista previa de impresión", 720x1600)
con etiquetas YOLO. Divide por TICKET (no por imagen) para evitar fuga entre
train/val/test.

Uso:
    python gen_tickets.py --out dataset --n-tickets 300 --crops 3
    python gen_tickets.py --out dataset --n-tickets 20 --crops 2 --preview   # prueba rápida

Los datos son sintéticos: decláralo así en tu ficha (sección 10 de las bases).
"""
import argparse, random, os, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ----------------------------------------------------------------- clases
# Edita esta lista si necesitas otras. El orden define el id YOLO.
CLASSES = [
    "producto",         # 0 línea de descripción del producto
    "proveedor",        # 1 nombre del proveedor (tras "Proveedor :")
    "precio_unitario",  # 2
    "cantidad",         # 3
    "subtotal",         # 4 subtotal de línea en VENTA
    "subtotal_dev",     # 5 subtotal de línea en DEVOLUCION (entre paréntesis)
    "total_venta",      # 6
    "total_devoluciones",  # 7
    "monto_neto",       # 8
    "total_impuestos",  # 9
    "descuento_total",  # 10
    "peso_total",       # 11
    "cantidad_entregar",  # 12
    "cliente",          # 13
    "fecha",            # 14
    "seccion",          # 15 encabezados VENTA / DEVOLUCION / CORTESIA
    "folio",            # 16 número de nota
]
CID = {c: i for i, c in enumerate(CLASSES)}

# ----------------------------------------------------------------- layout (medido de tus capturas)
W, H = 720, 1600
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = 20           # ancho de carácter ~12 px, como en las referencias
LINE_H = 23.6
X0 = 130
VIEW_TOP, VIEW_BOT = 232, 1490   # área donde se ve el texto (entre barra y botones)
COLS = 37
BLUE_TOP = (0, 51, 128)
BLUE_BAR = (21, 101, 192)

PRODUCTS = [
    "DANONE GRIEGO BEBIBLE DURAZNO 435G", "DANY FRESA 125G", "DANONINO BEBIBLE FRESA 170G",
    "DANONE FRESA 220G DS ASS", "DANONINO BEBIBLE FRESA 90G", "OIKOS COCO 125G",
    "NOM DANUP CREMA Y GALLETAS 220G", "NOM DANUP FRESA 220G", "NOM DANUP PIÑA COCO 220G",
    "NOM DANY PIÑA 125G", "DANONE MANZANA 220G MIDGET", "DANONE DURAZNO 220G MIDGET",
    "BENEG NATURAL 240G", "DANUP PIÑA COCO 435G", "DANUP COOKIES & CREAM 435G",
    "DANUP FRESA 435G", "DANONE LICUADO NUEZ 435G", "DANONE LICUADO FRESA C/AVENA 435 G",
    "DANONE LICUADO PLATANO CANE C/AVENA", "NOM DANY UVA 125G", "ACTIVIA CIRUELA PASA 225G EVO N51",
    "ACTIVIA FRESA 225G EVO N51", "DANMIX VAINILLA M&Ms 110G", "DANONE GRIEGO BEBIBLE FRESA 435G",
    "OIKOS FRESA 125G", "NOM Danone Bipack Manza Estrll Aven", "NOM Danone Bipack Fresa Zucaradas 1",
    "DANONE LICUADO FRESA PLATANO 435G", "DANONE LICUADO FRUTOS ROJOS 435G",
    "DANONINO POUCH FRESA 70G MM", "BFT JUIZZY GUAYABA 1000MLX06PK180 N",
    "BONAFONT NATURAL 1500MLX12PK 56 N51", "BONAFONT NATURAL 1000MLX12PK 90 N51",
    "BONAFONT NATURAL 2000MLX06PK 44 N51", "ACTIVIA NATURAL 900G N51", "OIKOS NATURAL 900G",
]
TIENDAS = ["ABARROTES DON NACHO", "TIENDA LA ESPERANZA", "MISCELANEA LUPITA", "ABARROTES MARTHA",
           "SUPER EL SOL", "TIENDITA DOÑA MARY", "ABARROTES LOS ARCOS", "MISCELANEA EL GALLO"]
CALLES = ["CALLE  ALAMOS", "AV. JUAREZ 120", "CALLE REFORMA", "PRIV. HIDALGO", "CALLE MORELOS 45"]
VENDEDORES = ["0753067177 PEREZ LOPEZ ANA", "0753011220 LOPEZ CRUZ JUAN",
              "0753099841 SANTIAGO RAMIREZ ANA"]

_font = None
def font():
    global _font
    if _font is None:
        _font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    return _font

CW = None
def cw():
    global CW
    if CW is None:
        CW = font().getlength("0")
    return CW


# ----------------------------------------------------------------- construcción del ticket (líneas + etiquetas)
class Ticket:
    """Lista de líneas; cada línea = (texto, [(clase, col_ini, col_fin), ...])."""
    def __init__(self):
        self.lines = []

    def add(self, text="", labels=()):
        text = text[:COLS + 3]
        self.lines.append((text, list(labels)))

    def wrap(self, text, labels_cls=None):
        # envuelve a 37 columnas, como la impresora
        while len(text) > COLS:
            self.add(text[:COLS]); text = text[COLS:]
        self.add(text)


def money(v):
    return f"${v:,.2f}"

def neg(v):
    return f"(${v:,.2f})"

def item_lines(t, name, sku, pu, qty, negative=False):
    name = name[:COLS]
    t.add(name, [("producto", 0, len(name))])
    sku_s, pu_s, qty_s = str(sku), money(pu), f"{qty:.1f}"
    sub = pu * qty
    sub_s = neg(sub) if negative else money(sub)
    line = f"{sku_s} {pu_s}"
    pu_c0 = len(sku_s) + 1
    line = line.ljust(18) + qty_s
    q_c0 = 18
    end = 36 if negative else 35
    line = line.ljust(end - len(sub_s)) + sub_s
    s_c0 = end - len(sub_s)
    t.add(line, [("precio_unitario", pu_c0, pu_c0 + len(pu_s)),
                 ("cantidad", q_c0, q_c0 + len(qty_s)),
                 ("subtotal_dev" if negative else "subtotal", s_c0, s_c0 + len(sub_s))])
    return sub


def hdr(t, title):
    t.add("*" * COLS)
    t.add(title, [("seccion", 0, len(title))])
    t.add("-" * COLS)
    t.add("Descripción")
    t.add("SKU    P.U.       Qty.   Sub Total")
    t.add("-" * COLS)


def build_ticket(rng):
    t = Ticket()
    fecha = f"{rng.randint(1,28):02d}/{rng.randint(1,12):02d}/2026"
    cliente = f"07{rng.randint(10000000,99999999)}"
    tienda = rng.choice(TIENDAS)
    ruta = f"17000{rng.randint(10000,99999)} (MX 590_{rng.randint(1000,2999)} RUTA PV {rng.randint(1,20):02d})"

    if rng.random() < 0.6:   # ticket completo con encabezado
        t.add("NOTA DE VENTA".center(COLS))
        num = f"18018{rng.randint(10**12,10**13-1)}"
        ln = f"Numero : {num}".center(COLS)
        t.add(ln, [("folio", ln.index(num), ln.index(num) + len(num))])
        t.add()
        s = f"Fecha de emision : {fecha}"
        t.add(s, [("fecha", s.index(fecha), s.index(fecha) + len(fecha))])
        t.add("-" * COLS); t.add(); t.add("Proveedor :")
        prov = "DANONE DE MEXICO S.A. DE C.V."
        t.add(prov, [("proveedor", 0, len(prov))]); t.add("-" * COLS); t.add()
        t.add(f"ACOLMAN            {fecha}"); t.add()
        t.add("Establecimiento :"); t.add("DANONE DE MEXICO S.A. DE C.V."); t.add("Calle :")
        t.add("GUILLERMO GONZÁLEZ CAMARENA, 333"); t.add("Colonia :"); t.add()
        t.add("Ciudad : D.ALVARO OBREGON"); t.add("Codigo Postal : 1210"); t.add("-" * COLS)
    s = f"Cliente : {cliente}"
    t.add(s, [("cliente", 10, len(s))])
    t.add(f"Nombre : {tienda}"); t.add("Calle :"); t.add(rng.choice(CALLES))
    t.add("Colonia:"); t.add("Ciudad : OAXACA DE JUAREZ"); t.add("Estado :"); t.add("Codigo Postal :")
    t.add("*" * COLS); t.add("Ruta :"); t.wrap(ruta); t.add("Vendedor :")
    t.add(" " + rng.choice(VENDEDORES))

    # CORTESIA (casi siempre vacía)
    hdr(t, "CORTESIA")
    t.add("-" * COLS); t.add("*" * COLS); t.add("Total Unidades Cortesia : 0"); t.add()

    # DEVOLUCION
    hdr(t, "DEVOLUCION")
    n_dev = rng.choice([0, 0, 0, 1, 2, 3, 4])
    total_dev, units_dev = 0.0, 0.0
    if n_dev == 0:
        t.add("-" * COLS)
    for name in rng.sample(PRODUCTS, n_dev):
        pu = round(rng.choice([9.60, 13.70, 16.60, 15.20, 21.90, 24.80, 8.20]), 2)
        q = float(rng.choice([1, 1, 2]))
        total_dev += item_lines(t, name, rng.randint(100000, 219999), pu, q, negative=True)
        units_dev += q
    t.add()
    t.add("*" * COLS)
    t.add(f"Unidades a Retirar : {units_dev:.1f}")
    t.add(f"Importe Neto Dev : {neg(total_dev)}")
    t.add(); t.add("*" * COLS); t.add()

    # VENTA
    hdr(t, "VENTA")
    n = rng.choice([1, 2, 3, 5, 8, 12, 16, 20, 24])
    total_v, units = 0.0, 0.0
    for name in rng.sample(PRODUCTS, min(n, len(PRODUCTS))):
        pu = round(rng.choice([8.20, 9.60, 10.40, 12.20, 13.70, 13.80, 15.20, 15.80, 16.60,
                               19.70, 21.90, 24.80, 110.00, 160.00, 180.00, 230.00]), 2)
        q = float(rng.choice([1, 1, 1, 2, 2, 3, 4]))
        total_v += item_lines(t, name, rng.randint(100000, 219999), pu, q)
        units += q
    t.add("-" * COLS); t.add()

    peso = f"{rng.uniform(1, 60):.3f}"
    unit = rng.choice(["Kilos.", "Ltrs."])
    row = lambda label, val, cls: (
        t.add(f"{label} : {val}", [(cls, len(label) + 3, len(label) + 3 + len(val))]))
    imp = "$0" if rng.random() < 0.7 else money(total_v * 0.168)
    neto = total_v - total_dev
    row("Peso Total", f"{peso} {unit}", "peso_total")
    row("Cantidad a entregar", f"{units:.1f}", "cantidad_entregar")
    row("Descuento Total", "($0.00)", "descuento_total")
    row("Total Impuestos", imp, "total_impuestos")
    row("Total Venta", money(total_v), "total_venta")
    row("Total Devoluciones", neg(total_dev), "total_devoluciones")
    row("Monto Neto a Pagar", money(neto), "monto_neto")
    t.add(); t.add("*" * COLS); t.add()
    if rng.random() < 0.4:
        t.add(f"TOTAL A PAGAR : {money(neto)}"); t.add("PIEZAS ENTREGAR DANONE : 0")
        t.add(f"CAJAS ENTREGAR BONAFONT : {rng.randint(1,5)}.00"); t.add("*" * COLS); t.add()
    t.add("Consulte aviso de privacidad en:")
    t.add("https:\\\\www.grupodanone.com.mx\\aviso"); t.add("-privacidad.aspx"); t.add()
    return t


# ----------------------------------------------------------------- render
def render_full(t):
    """Imagen alta con todo el ticket + cajas [(cls, x0,y0,x1,y1)] en coords del lienzo."""
    f = font()
    h = int(len(t.lines) * LINE_H) + 40
    canvas = Image.new("RGB", (W, h), "white")
    d = ImageDraw.Draw(canvas)
    boxes = []
    asc, desc = f.getmetrics()
    for i, (text, labels) in enumerate(t.lines):
        y = 10 + i * LINE_H
        d.text((X0, y), text, font=f, fill=(25, 25, 25))
        for cls, c0, c1 in labels:
            bx0 = X0 + c0 * cw(); bx1 = X0 + c1 * cw()
            boxes.append((cls, bx0 - 1, y + 3, bx1 + 1, y + 3 + FONT_SIZE))
    return canvas, boxes


def chrome(img_view, rng, scroll_top_clipped=True):
    """Pega el contenido en una captura con barra superior, 'Vista previa de impresión' y botones."""
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 29)
    # barras
    d.rectangle([0, 0, W, 72], fill=BLUE_TOP)
    d.rectangle([0, 72, W, 164], fill=BLUE_BAR)
    hh, mm = rng.randint(15, 18), rng.randint(0, 59)
    d.text((40, 24), f"{hh}:{mm:02d}", font=small, fill="white")
    d.text((590, 24), f"4G  {rng.choice([1,3,30,45,80])}%", font=small, fill="white")
    d.text((34, 100), "←", font=title, fill="white")
    d.text((118, 102), "Vista previa de impresión", font=title, fill="white")
    if rng.random() < 0.7:
        d.ellipse([660, 104, 690, 134], outline="white", width=3)
    # fila de impresora
    msg = rng.choice(["Conectando", "Reconecte la impresora nuevamente"])
    d.text((52, 196), msg, font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 21), fill=(130, 130, 130))
    d.polygon([(610, 205), (636, 205), (623, 217)], fill=(120, 120, 120))
    # contenido
    im.paste(img_view, (0, VIEW_TOP))
    # barra de navegación
    d.rectangle([0, VIEW_BOT, W, H], fill="black")
    d.polygon([(170, 1545), (195, 1528), (195, 1562)], fill="white")
    d.ellipse([338, 1527, 372, 1561], fill="white")
    d.rectangle([510, 1528, 538, 1558], fill="white")
    return im


def augment(im, rng):
    if rng.random() < 0.5:
        im = ImageEnhance.Brightness(im).enhance(rng.uniform(0.92, 1.06))
    if rng.random() < 0.3:
        im = im.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.8)))
    return im


def crops_from_ticket(canvas, boxes, rng, k):
    vh = VIEW_BOT - VIEW_TOP
    max_scroll = max(0, canvas.height - vh)
    tops = sorted({0 if i == 0 else rng.randint(0, max_scroll) for i in range(k)}) if max_scroll else [0]
    out = []
    for top in tops:
        view = canvas.crop((0, top, W, top + vh))
        if view.height < vh:
            padded = Image.new("RGB", (W, vh), "white"); padded.paste(view, (0, 0)); view = padded
        lab = []
        for cls, x0, y0, x1, y1 in boxes:
            y0c, y1c = max(y0 - top, 0), min(y1 - top, vh)
            if y1c <= y0c or (y1c - y0c) / (y1 - y0) < 0.6:   # corte excesivo -> sin etiqueta
                continue
            lab.append((cls, x0, y0c + VIEW_TOP, x1, y1c + VIEW_TOP))
        out.append((view, lab))
    return out


def yolo_line(cls, x0, y0, x1, y1):
    return f"{CID[cls]} {(x0+x1)/2/W:.6f} {(y0+y1)/2/H:.6f} {(x1-x0)/W:.6f} {(y1-y0)/H:.6f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--n-tickets", type=int, default=300)
    ap.add_argument("--crops", type=int, default=3, help="capturas (scroll distinto) por ticket")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--preview", action="store_true", help="dibuja las cajas sobre las imágenes (carpeta preview/)")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    out = Path(a.out)
    ids = list(range(a.n_tickets))
    rng.shuffle(ids)
    n_tr, n_va = int(0.8 * a.n_tickets), int(0.1 * a.n_tickets)
    split_of = {tid: ("train" if i < n_tr else "val" if i < n_tr + n_va else "test") for i, tid in enumerate(ids)}
    for s in ("train", "val", "test"):
        (out / "images" / s).mkdir(parents=True, exist_ok=True)
        (out / "labels" / s).mkdir(parents=True, exist_ok=True)
    if a.preview:
        (out / "preview").mkdir(exist_ok=True)

    counts = {"train": 0, "val": 0, "test": 0}
    for tid in range(a.n_tickets):
        t = build_ticket(rng)
        canvas, boxes = render_full(t)
        split = split_of[tid]
        for j, (view, lab) in enumerate(crops_from_ticket(canvas, boxes, rng, a.crops)):
            im = augment(chrome(view, rng), rng)
            name = f"tk{tid:05d}_{j}"
            im.save(out / "images" / split / f"{name}.jpg", quality=rng.randint(80, 95))
            (out / "labels" / split / f"{name}.txt").write_text("\n".join(yolo_line(*l) for l in lab) + "\n")
            counts[split] += 1
            if a.preview and tid < 10:
                p = im.copy(); dd = ImageDraw.Draw(p)
                for cls, x0, y0, x1, y1 in lab:
                    dd.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=2)
                p.save(out / "preview" / f"{name}.png")

    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\n"
        f"nc: {len(CLASSES)}\nnames: {json.dumps(CLASSES, ensure_ascii=False)}\n")
    print("Listo:", counts, "->", out.resolve())


if __name__ == "__main__":
    main()
