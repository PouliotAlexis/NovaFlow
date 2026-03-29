// NovaFlow Simple Moodle Extension - background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "UPDATE_SESSION" || request.action === "UPDATE_TOKEN") {
        const data = request.data;
        
        // 1. Sauvegarder localement
        chrome.storage.local.set({ 
            status: "Connecté", 
            hasToken: request.action === "UPDATE_TOKEN",
            hasSesskey: request.action === "UPDATE_SESSION",
            lastCapturedHost: data.host, 
            lastCapturedTime: new Date().toLocaleTimeString(),
            sessionData: data
        });

        // 2. Diffuser à tous les onglets NovaFlow ouverts (Client-Side Persistence)
        chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
                if (tab.url && (tab.url.includes("localhost:3000") || tab.url.includes("vercel.app"))) {
                    chrome.tabs.sendMessage(tab.id, request);
                }
            });
        });

        // 3. (Optionnel) Envoyer aux backends connus si configurés
        const BACKENDS = [
            "http://localhost:8000/api/v2/moodle/session/update",
            "https://nova-flow-mu.vercel.app/api/v2/moodle/session/update"
        ];
        BACKENDS.forEach(url => {
            fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            }).catch(() => {});
        });
    }
});
