// NovaFlow Simple Moodle Extension - background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "REGISTER_BACKEND") {
        chrome.storage.local.get(['knownBackends'], (result) => {
            let backends = result.knownBackends || [];
            if (!backends.includes(request.origin)) {
                backends.push(request.origin);
                chrome.storage.local.set({ knownBackends: backends });
                console.log("NovaFlow: Nouveau backend enregistré : " + request.origin);
            }
        });
        return;
    }

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
                    // Ignorer les onglets qui n'ont pas fini de charger le script de réception
                    chrome.tabs.sendMessage(tab.id, request).catch(() => {});
                }
            });
        });

        // 3. Envoyer directement au backend de production (Render)
        const BACKENDS = [
            "https://novaflow-9lj7.onrender.com/api/v2/moodle/session/update"
        ];
        chrome.storage.local.get(['knownBackends'], (result) => {
            const backends = result.knownBackends || [];
            // On ignore knownBackends pour l'instant car ce sont les URLs du frontend
            const targets = [...BACKENDS];
            
            targets.forEach(url => {
                fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data),
                    credentials: 'include'
                })
                .then(r => console.log(`NovaFlow: ✅ Envoyé à ${url}`))
                .catch(err => console.log(`NovaFlow: ❌ Serveur ${url} injoignable.`));
            });
        });
    }
});
