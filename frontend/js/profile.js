
async function actualizarPerfil() {

    const token = sessionStorage.getItem("access_token");

    const usuario = JSON.parse(
        sessionStorage.getItem("usuario")
    );

    const datos = {

        nombre: document.getElementById("profileNombre").value,

        apellido: document.getElementById("profileApellido").value,

        correo: document.getElementById("profileCorreo").value,

        telefono: document.getElementById("profileTelefono").value

    };

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/usuarios/me/",
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },

                body: JSON.stringify(datos)
            }
        );

        const resultado = await response.json();

        if (!response.ok) {

            alert(resultado.detail || "No se pudieron actualizar los datos.");

            return;
        }

        // Actualizar información local
        sessionStorage.setItem(
            "usuario",
            JSON.stringify(resultado.usuario)
        );

        // Actualizar nombre del perfil
        cargarPerfil();

        alert("¡Tus datos se actualizaron correctamente!");

    } catch (error) {

        console.error("Error actualizando perfil:", error);

        alert("Error de conexión con el servidor.");

    }

}

function cargarNombreInicio() {

    const usuario = JSON.parse(
        sessionStorage.getItem("usuario") || "{}"
    );

    document.getElementById("welcomeName").textContent =
        usuario.nombre || "Usuario";
}