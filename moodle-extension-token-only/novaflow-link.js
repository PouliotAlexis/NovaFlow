// NovaFlow Bridge Script - novaflow-link.js
// Runs on NovaFlow site to receive tokens from extension background

console.log("NovaFlow Bridge: Active");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "UPDATE_TOKEN" || request.action === "UPDATE_SESSION") {
        console.log("NovaFlow Bridge: Reçu session de l'extension, relais vers le site...");
        window.postMessage({
            type: "NOVAFLOW_MOODLE_SESSION",
            data: request.data
        }, "*");
    }
});

// Permettre au site de demander la session actuelle au chargement
window.addEventListener("message", (event) => {
    if (event.data.type === "GET_NOVAFLOW_EXTENSION_STATUS") {
        chrome.storage.local.get(['status', 'hasToken', 'hasSesskey', 'lastCapturedHost'], (data) => {
             window.postMessage({
                 type: "NOVAFLOW_EXTENSION_STATUS",
                 data: data
             }, "*");
        });
    }
});
