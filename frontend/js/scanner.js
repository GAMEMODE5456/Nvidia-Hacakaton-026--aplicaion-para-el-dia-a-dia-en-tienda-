
const API_URL = "http://127.0.0.1:8000";

// ELEMENTOS DEL ESCÁNER
const ticketImage = document.getElementById("ticketImage");
const ticketPreview = document.getElementById("ticketPreview");
const btnAnalyzeTicket = document.getElementById("btnAnalyzeTicket");
const ticketResult = document.getElementById("ticketResult");

// 1. MOSTRAR LA IMAGEN SELECCIONADA
ticketImage.addEventListener("change", function () {
    const imagen = this.files[0];

    if (!imagen) {
        return;
    }

    if (!imagen.type.startsWith("image/")) {
        alert("Selecciona una imagen válida.");
        this.value = "";
        return;
    }

    ticketPreview.src = URL.createObjectURL(imagen);
    ticketPreview.classList.remove("hidden");

    ticketResult.textContent = "";
    btnAnalyzeTicket.disabled = false;
});

// 2. ENVIAR EL TICKET AL MODELO DE IA
btnAnalyzeTicket.addEventListener("click", async function () {

    const imagen = ticketImage.files[0];

    if (!imagen) {
        alert("Primero selecciona una fotografía del ticket.");
        return;
    }

    // Obtener el usuario que inició sesión
    const usuarioGuardado = sessionStorage.getItem("usuario");

    let idUsuario = 1;

    if (usuarioGuardado) {
        const usuario = JSON.parse(usuarioGuardado);
        idUsuario = usuario.id_usuario || 1;
    }

    // Preparar los datos para FastAPI
    const formData = new FormData();
    formData.append("imagen", imagen);

    try {

        btnAnalyzeTicket.disabled = true;
        btnAnalyzeTicket.textContent = "Analizando ticket...";
        ticketResult.textContent = "La inteligencia artificial está leyendo tu ticket...";

        const response = await fetch(
            `${API_URL}/ia/leer-ticket?id_usuario=${idUsuario}`,
            {
                method: "POST",
                body: formData
            }
        );

        const resultado = await response.json();

        if (!response.ok) {
            throw new Error(
                resultado.detail
                    ? JSON.stringify(resultado.detail)
                    : "Error al analizar el ticket"
            );
        }

        console.log("Resultado de la IA:", resultado);

        // Mostrar la respuesta de la IA
        ticketResult.textContent =
            typeof resultado === "string"
                ? resultado
                : JSON.stringify(resultado, null, 2);

    } catch (error) {

        console.error("Error al analizar ticket:", error);

        ticketResult.textContent = "No se pudo analizar el ticket: " + error.message;

    } finally {

        btnAnalyzeTicket.disabled = false;
        btnAnalyzeTicket.textContent = "Analizar ticket";

    }

});
