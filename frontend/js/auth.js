const API_URL = "http://127.0.0.1:8000";

// REGISTRAR USUARIO
document.getElementById("registerForm").addEventListener("submit", async function(event) {

    event.preventDefault();

    const nombre = document.getElementById("registerName").value.trim();
    const apellido = document.getElementById("registerApellido").value.trim();
    const correo = document.getElementById("registerEmail").value.trim();
    const telefono = document.getElementById("registerTelefono").value.trim();
    const password = document.getElementById("registerPassword").value;

    const usuario = {
        nombre: nombre,
        apellido: apellido,
        correo: correo,
        telefono: telefono,
        password: password
    };

    try {

        const response = await fetch(`${API_URL}/usuarios/registro`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(usuario)

        });

        const data = await response.json();

        console.log("Respuesta del servidor:", data);

        if (!response.ok) {

            alert(data.detail || "No se pudo registrar el usuario");

            return;
        }

        alert("¡Cuenta creada correctamente!");

        document.getElementById("registerForm").reset();

        document.getElementById("register").classList.add("hidden");

        document.getElementById("login").classList.remove("hidden");

    } catch (error) {

        console.error("Error al registrar:", error);

        alert("No se pudo conectar con el servidor FastAPI");

    }

});l