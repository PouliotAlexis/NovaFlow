/**
 * Service Worker en arrière-plan pour gérer les communications
 * et la file d'attente d'envoi vers NovaFlow.
 */

// Port local du serveur NovaFlow
const NOVAFLOW_URL = "http://localhost:8000/api/moodle/sync";

// Écoute des messages venant du content_script.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "SYNC_MOODLE_EVENTS") {
        const events = request.data;
        if (events && events.length > 0) {
            syncToNovaFlow(events);
        }
    }
});

async function syncToNovaFlow(events) {
    try {
        const payload = {
            source: "moodle_extension",
            timestamp: new Date().toISOString(),
            events: events
        };

        const response = await fetch(NOVAFLOW_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            console.log("Synchronisation NovaFlow réussie !");
            updateBadgeStatus("OK", "#22c55e"); // Vert

            // Stocker le nombre pour le popup
            chrome.storage.local.set({
                lastSyncTime: new Date().toLocaleString(),
                lastSyncCount: events.length,
                syncStatus: "success"
            });
        } else {
            console.warn("Le serveur NovaFlow a retourné une erreur :", response.status);
            handleSyncFailure(events);
        }

    } catch (error) {
        // Le serveur est probablement fermé (net::ERR_CONNECTION_REFUSED)
        console.warn("Impossible de joindre le serveur NovaFlow. Serveur fermé ?");
        handleSyncFailure(events);
    }
}

function handleSyncFailure(events) {
    updateBadgeStatus("ERR", "#ef4444"); // Rouge

    // On met en cache pour plus tard
    chrome.storage.local.set({
        queuedEvents: events,
        lastSyncTime: new Date().toLocaleString(),
        syncStatus: "failed"
    });
}

function updateBadgeStatus(text, color) {
    chrome.action.setBadgeText({ text: text });
    chrome.action.setBadgeBackgroundColor({ color: color });

    // Effacer le badge après 5 secondes
    setTimeout(() => {
        chrome.action.setBadgeText({ text: "" });
    }, 5000);
}

// Optionnel: On pourrait ajouter une alarme (chrome.alarms) pour retenter la synchronisation
// des queuedEvents toutes les X minutes si on détecte que le serveur est de retour en ligne.
