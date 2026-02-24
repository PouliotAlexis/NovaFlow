document.addEventListener('DOMContentLoaded', () => {
    const syncDateEl = document.getElementById('syncDate');
    const syncCountEl = document.getElementById('syncCount');
    const fileCountEl = document.getElementById('fileCount');
    const syncStateEl = document.getElementById('syncState');
    const statusBox = document.getElementById('statusBox');

    // Charger l'état depuis le background storage
    chrome.storage.local.get(['lastSyncTime', 'lastSyncCount', 'syncStatus', 'moodleSesskey', 'downloadedMoodleFiles'], (data) => {
        if (data.lastSyncTime) {
            syncDateEl.textContent = data.lastSyncTime;
        }

        if (data.lastSyncCount !== undefined) {
            syncCountEl.textContent = data.lastSyncCount;
        }

        if (data.downloadedMoodleFiles) {
            fileCountEl.textContent = Object.keys(data.downloadedMoodleFiles).length;
        }


        if (data.syncStatus === 'success') {
            syncStateEl.textContent = 'Succès';
            statusBox.className = 'status status-success';
        } else if (data.syncStatus === 'failed') {
            syncStateEl.textContent = `Serveur distant injoignable`;
            statusBox.className = 'status status-failed';
        }

        // Si l'utilisateur n'a jamais ouvert Moodle, on lui indique
        if (!data.moodleSesskey) {
            syncStateEl.textContent = "Aucune session Moodle trouvée";
            statusBox.className = 'status status-failed';
        }
    });

    document.getElementById('btnRetry').addEventListener('click', () => {
        chrome.storage.local.get(['moodleSesskey'], (data) => {
            if (data.moodleSesskey) {
                // Envoyer un message au background pour forcer l'essai
                chrome.runtime.sendMessage({ action: "FORCE_BACKGROUND_SYNC" });

                syncStateEl.textContent = 'Synchronisation en cours...';
                statusBox.className = 'status status-pending';

                // Rafraichir l'interface après 2 secondes pour voir le résultat
                setTimeout(() => window.location.reload(), 2000);
            } else {
                alert("Impossible de synchroniser : Ouvre d'abord un onglet Moodle pour capturer ta session !");
            }
        });
    });
});
