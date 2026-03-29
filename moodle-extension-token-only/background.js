// NovaFlow Simple Moodle Extension - background.js

const BACKEND_URL = "https://nova-flow-mu.vercel.app/api/v2/moodle/session/update";
const LOCAL_BACKEND_URL = "http://localhost:8000/api/v2/moodle/session/update";

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "UPDATE_TOKEN" || request.action === "UPDATE_SESSION") {
        const data = request.data;
        console.log("NovaFlow Extension: Données reçues...", data);

        // Sauvegarder l'état local pour le popup
        chrome.storage.local.set({
            lastCapturedHost: data.host,
            lastCapturedTime: new Date().toLocaleTimeString(),
            status: "Connecté"
        });

        // Envoyer aux deux backends
        [BACKEND_URL, LOCAL_BACKEND_URL].forEach(url => {
            fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            })
            .then(r => console.log(`NovaFlow: Sync OK vers ${url}`))
            .catch(err => console.log(`NovaFlow: Serveur ${url} injoignable.`));
        });
    }
});
