document.addEventListener('DOMContentLoaded', () => {
    const syncDateEl = document.getElementById('syncDate');
    const syncCountEl = document.getElementById('syncCount');
    const syncStateEl = document.getElementById('syncState');
    const statusBox = document.getElementById('statusBox');

    // Charger l'état depuis le background storage
    chrome.storage.local.get(['lastSyncTime', 'lastSyncCount', 'syncStatus', 'queuedEvents'], (data) => {
        if (data.lastSyncTime) {
            syncDateEl.textContent = data.lastSyncTime;
        }

        if (data.lastSyncCount !== undefined) {
            syncCountEl.textContent = data.lastSyncCount;
        }

        if (data.syncStatus === 'success') {
            syncStateEl.textContent = 'Succès';
            statusBox.className = 'status status-success';
        } else if (data.syncStatus === 'failed') {
            const queueCount = data.queuedEvents ? data.queuedEvents.length : 0;
            syncStateEl.textContent = `Serveur introuvable (${queueCount} en cache)`;
            statusBox.className = 'status status-failed';
        }
    });

    document.getElementById('btnRetry').addEventListener('click', () => {
        chrome.storage.local.get(['queuedEvents'], (data) => {
            if (data.queuedEvents && data.queuedEvents.length > 0) {
                // Envoyer un message au background pour forcer l'essai
                chrome.runtime.sendMessage({
                    action: "SYNC_MOODLE_EVENTS",
                    data: data.queuedEvents
                });

                syncStateEl.textContent = 'Nouvel essai...';
                statusBox.className = 'status status-pending';
            } else {
                alert("Aucun événement local en cache ! Ouvre d'abord ton onglet Moodle.");
            }
        });
    });
});
