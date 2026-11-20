
// =============================================
// ESCANER DE TICKETS
// Toma foto, ejecuta OCR y guarda en MariaDB
// =============================================

const API_URL = window.location.origin;
const URL_OCR = `${API_URL}/ocr/leer-ticket`;
const MAX_MB = 12;

const $ = (id) => document.getElementById(id);

const ticketImage = $("ticketImage");
const ticketPreview = $("ticketPreview");
const btnAnalyzeTicket = $("btnAnalyzeTicket");
const ticketResult = $("ticketResult");
const ticketStatus = $("ticketStatus");
const ticketTable = $("ticketTable");

let ultimoJSON = null;

function aviso(texto, tipo = "info") {
    if (!ticketStatus) return;

    ticketStatus.textContent = texto;
    ticketStatus.dataset.tipo = tipo;

    ticketStatus.setAttribute(
        "role",
        tipo === "error" ? "alert" : "status"
    );
}

function idUsuarioActual() {
    try {
        const u = JSON.parse(
            sessionStorage.getItem("usuario") || "null"
        );

        return (u && u.id_usuario) || 1;

    } catch {
        return 1;
    }
}

function dinero(n) {
    return typeof n === "number"
        ? n.toLocaleString("es-MX", {
            style: "currency",
            currency: "MXN"
        })
        : "—";
}

function esc(v) {
    return String(v ?? "").replace(
        /[&<>"']/g,
        (c) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[c])
    );
}

// =============================================
// MOSTRAR PRODUCTOS DEL TICKET
// =============================================

function pintarTabla(ticket) {

    if (!ticketTable) return;

    const filas = (ticket.productos || [])
        .map((p) => `
            <tr>
                <td>${esc(p.nombre)}</td>
                <td>${esc(p.presentacion ?? "—")}</td>
                <td>${esc(p.cantidad)}</td>
                <td>${dinero(p.precio_unitario)}</td>
            </tr>
        `)
        .join("");

    ticketTable.innerHTML = `
        <p>
            <strong>Proveedor:</strong>
            ${esc(ticket.proveedor ?? "No detectado")}<br>

            <strong>Folio:</strong>
            ${esc(ticket.folio ?? "No detectado")}<br>

            <strong>Fecha:</strong>
            ${esc(ticket.fecha_compra ?? "No detectada")}<br>

            <strong>Total:</strong>
            ${dinero(ticket.total)}
        </p>

        <table>
            <caption>Productos detectados</caption>

            <thead>
                <tr>
                    <th>Producto</th>
                    <th>Presentación</th>
                    <th>Cantidad</th>
                    <th>Precio unitario</th>
                </tr>
            </thead>

            <tbody>
                ${filas || `
                    <tr>
                        <td colspan="4">Sin productos</td>
                    </tr>
                `}
            </tbody>
        </table>
    `;
}

// =============================================
// 1. VISTA PREVIA DE LA FOTOGRAFÍA
// =============================================

ticketImage.addEventListener("change", () => {

    const imagen = ticketImage.files[0];

    if (!imagen) return;

    if (!imagen.type.startsWith("image/")) {

        aviso(
            "Selecciona una imagen válida JPG o PNG.",
            "error"
        );

        ticketImage.value = "";
        return;
    }

    if (imagen.size > MAX_MB * 1024 * 1024) {

        aviso(
            `La imagen pesa más de ${MAX_MB} MB.`,
            "error"
        );

        ticketImage.value = "";
        return;
    }

    if (ticketPreview.dataset.previewUrl) {
        URL.revokeObjectURL(ticketPreview.dataset.previewUrl);
    }

    const previewUrl = URL.createObjectURL(imagen);

    ticketPreview.src = previewUrl;
    ticketPreview.dataset.previewUrl = previewUrl;

    ticketPreview.classList.remove("hidden");
    ticketPreview.alt = "Vista previa del ticket";

    ticketResult.textContent = "";

    if (ticketTable) {
        ticketTable.innerHTML = "";
    }

    ultimoJSON = null;

    btnAnalyzeTicket.disabled = false;

    aviso(
        "Imagen lista. Presiona Analizar ticket.",
        "info"
    );
});

// =============================================
// 2. ENVIAR IMAGEN AL OCR Y GUARDAR
// =============================================

btnAnalyzeTicket.addEventListener("click", async () => {

    const imagen = ticketImage.files[0];

    if (!imagen) {

        aviso(
            "Primero toma o sube una foto del ticket.",
            "error"
        );

        return;
    }

    const formData = new FormData();

    formData.append("imagen", imagen);

    const controlador = new AbortController();

    const limite = setTimeout(
        () => controlador.abort(),
        120000
    );

    try {

        btnAnalyzeTicket.disabled = true;

        btnAnalyzeTicket.textContent = "Analizando y guardando...";

        btnAnalyzeTicket.setAttribute(
            "aria-busy",
            "true"
        );

        aviso(
            "Leyendo el ticket y guardando en MariaDB...",
            "info"
        );

        const resp = await fetch(
            `${URL_OCR}?id_usuario=${encodeURIComponent(idUsuarioActual())}`,
            {
                method: "POST",
                body: formData,
                signal: controlador.signal
            }
        );

        let datos = null;

        try {
            datos = await resp.json();
        } catch {
            throw new Error(
                "El servidor no devolvió una respuesta JSON válida."
            );
        }

        if (!resp.ok) {

            const detalle = datos?.detail;

            throw new Error(
                typeof detalle === "string"
                    ? detalle
                    : `Error ${resp.status} al procesar el ticket.`
            );
        }

        if (!datos.guardado || !datos.id_ticket) {
            throw new Error(
                "El OCR terminó, pero no se confirmó el guardado."
            );
        }

        // Guardar resultado completo
        ultimoJSON = {
            id_usuario: datos.id_usuario,
            id_ticket: datos.id_ticket,
            id_proveedor: datos.id_proveedor,
            guardado: datos.guardado,
            mensaje: datos.mensaje,
            ticket: datos.ticket
        };

        console.log(
            "Ticket procesado y guardado:",
            datos
        );

        // Mostrar información
        pintarTabla(datos.ticket);

        ticketResult.textContent = JSON.stringify(
            ultimoJSON,
            null,
            2
        );

        aviso(
            `¡Ticket guardado correctamente! ID: ${datos.id_ticket}`,
            "ok"
        );

        if (
            datos.advertencias &&
            datos.advertencias.length
        ) {
            aviso(
                `Ticket guardado. Advertencias: ${datos.advertencias.join(" ")}`,
                "info"
            );
        }

    } catch (e) {

        console.error("Error al procesar ticket:", e);

        const msg =
            e.name === "AbortError"
                ? "El servidor tardó demasiado. Intenta nuevamente."
                : e instanceof TypeError
                    ? "No se pudo conectar con el servidor."
                    : e.message;

        aviso(msg, "error");

    } finally {

        clearTimeout(limite);

        btnAnalyzeTicket.disabled = false;

        btnAnalyzeTicket.textContent = "Analizar ticket";

        btnAnalyzeTicket.removeAttribute("aria-busy");
    }
});

// =============================================
// 3. DISPONER DEL TICKET LEÍDO
// =============================================

window.obtenerTicketLeido = () => ultimoJSON;
