
function showScreen(screenId) {

    document.getElementById("login").classList.add("hidden");
    document.getElementById("register").classList.add("hidden");

    document.getElementById("application").classList.remove("hidden");

    document.querySelectorAll(".page").forEach(page => {
        page.classList.add("hidden");
    });

    const selectedPage = document.getElementById(screenId);

    if (selectedPage) {
        selectedPage.classList.remove("hidden");
    }

    document.querySelectorAll(".bottom-nav button").forEach(button => {
        button.classList.remove("active");
    });

    const navigation = {
        home: 0,
        history: 1,
        payments: 2,
        profile: 3
    };

    const navButtons = document.querySelectorAll(".bottom-nav button");

    if (navigation[screenId] !== undefined) {
        navButtons[navigation[screenId]].classList.add("active");
    }

    if (screenId === "home") {
        cargarNombreInicio();
    }

    if (screenId === "profile") {
        cargarPerfil();
    }
}
