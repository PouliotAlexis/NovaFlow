// NovaFlow Simple Moodle Extension - content.js

console.log("%c NovaFlow Simple Extension %c Content script starting...", "background:#38bdf8; color:white; padding:2px; border-radius:3px;", "");

async function findAndSendToken() {
    console.log("NovaFlow: Scanning for session...");
    
    const host = window.location.origin;

    // 1. Chercher le token mobile dans l'URL (le Graal)
    const url = window.location.href;
    if (url.includes("token=")) {
        const token = url.split("token=")[1].split("&")[0];
        console.log("NovaFlow: ✅ Token Mobile trouvé dans l'URL !");
        chrome.runtime.sendMessage({ action: "UPDATE_TOKEN", data: { token, host } });
        return;
    }

    // 2. Chercher un lien moodlemobile:// dans la page
    const links = document.querySelectorAll('a[href^="moodlemobile://"]');
    if (links.length > 0) {
        for (const link of links) {
            if (link.href.includes("token=")) {
                const token = link.href.split("token=")[1].split("&")[0];
                console.log("NovaFlow: ✅ Token trouvé dans un lien sur la page !");
                chrome.runtime.sendMessage({ action: "UPDATE_TOKEN", data: { token, host } });
                return;
            }
        }
    }

    // 3. Fallback: Chercher la sesskey ET tenter de forcer un token
    const sesskey = window?.M?.cfg?.sesskey || document.querySelector('a[href*="logout.php?sesskey="]')?.href?.split('sesskey=')[1] || null;
    
    if (sesskey) {
        console.log("NovaFlow: ✅ Session (sesskey) détectée.");
        chrome.runtime.sendMessage({
            action: "UPDATE_SESSION",
            data: { sesskey: sesskey, host: host }
        });

        // TENTER UNE CAPTURE SILENCIEUSE DU TOKEN REST
        try {
            console.log("NovaFlow: Tentative de capture silencieuse du Token REST...");
            const launchUrl = `${host}/admin/tool/mobile/launch.php?service=moodle_mobile_app&urlscheme=moodlemobile`;
            const response = await fetch(launchUrl);
            const text = await response.text();
            
            if (text.includes("moodlemobile://token=")) {
                const token = text.split("moodlemobile://token=")[1].split('"')[0].split("'")[0];
                console.log("NovaFlow: ✅ Token REST capturé en arrière-plan !");
                chrome.runtime.sendMessage({ action: "UPDATE_TOKEN", data: { token, host } });
            }
        } catch (e) {
            console.warn("NovaFlow: Échec de la capture silencieuse (normal si pas sur la bonne page).");
        }
    }
}

// Lancement immédiat et périodique
findAndSendToken();
setInterval(findAndSendToken, 5000);

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
