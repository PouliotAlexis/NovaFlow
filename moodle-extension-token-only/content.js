// NovaFlow Simple Moodle Extension - content.js

console.log("NovaFlow Simple Extension: Loaded.");

function findAndSendToken() {
    // 1. Chercher dans l'URL (si on est sur la page de redirection)
    const url = window.location.href;
    if (url.includes("token=")) {
        const token = url.split("token=")[1].split("&")[0];
        sendToken(token);
        return;
    }

    // 2. Chercher un lien moodlemobile:// dans la page
    const links = document.querySelectorAll('a[href^="moodlemobile://"]');
    for (const link of links) {
        if (link.href.includes("token=")) {
            const token = link.href.split("token=")[1].split("&")[0];
            sendToken(token);
            return;
        }
    }

    // 3. Fallback: Chercher la sesskey pour les fonctions de base si le token est indisponible
    const sesskey = window?.M?.cfg?.sesskey || null;
    if (sesskey) {
        chrome.runtime.sendMessage({
            action: "UPDATE_SESSION",
            data: { sesskey: sesskey, host: window.location.origin }
        });
    }
}

function sendToken(token) {
    console.log("NovaFlow Simple Extension: Token détecté ! Envoi...");
    chrome.runtime.sendMessage({
        action: "UPDATE_TOKEN",
        data: { token: token, host: window.location.origin }
    });
}

// Exécuter au chargement
findAndSendToken();

// Surveiller les changements de DOM (pour les sites dynamiques)
const observer = new MutationObserver(findAndSendToken);
observer.observe(document.body, { childList: true, subtree: true });
