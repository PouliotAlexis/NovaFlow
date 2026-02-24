// NovaFlow Moodle Extension - content.js
// Injecté sur les pages Moodle pour extraire la clé de session et déléguer l'extraction en arrière-plan

console.log("NovaFlow Moodle Extension content script loaded.");

function captureSessionData() {
    try {
        console.log("NovaFlow: Recherche de la clé de session Moodle (sesskey)...");
        const logoutLink = document.querySelector('a[href*="logout.php?sesskey="]');
        if (!logoutLink) {
            console.log("NovaFlow: sesskey introuvable. Utilisateur non connecté ou thème non standard.");
            return;
        }

        const sesskey = new URL(logoutLink.href).searchParams.get('sesskey');
        if (!sesskey) {
            console.log("NovaFlow: Impossible d'extraire la sesskey de l'URL.");
            return;
        }

        const moodleHost = window.location.origin;

        console.log("NovaFlow: sesskey et host trouvés, envoi au background script...");

        chrome.runtime.sendMessage({
            action: "UPDATE_MOODLE_SESSION",
            data: {
                sesskey: sesskey,
                host: moodleHost,
                url: window.location.href
            }
        });

    } catch (err) {
        console.error("NovaFlow: Erreur critique lors de la capture de session:", err);
    }
}

// Run the capture
captureSessionData();

// Optional: refresh if user clicks around
document.addEventListener('click', (e) => {
    if (e.target.closest('button') || e.target.closest('a')) {
        setTimeout(captureSessionData, 2000);
    }
});
