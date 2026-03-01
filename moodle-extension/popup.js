document.addEventListener('DOMContentLoaded', () => {
    const syncDateEl = document.getElementById('syncDate');
    const syncCountEl = document.getElementById('syncCount');
    const fileCountEl = document.getElementById('fileCount');
    const syncStateEl = document.getElementById('syncState');
    const statusBox = document.getElementById('statusBox');
    const btnRetry = document.getElementById('btnRetry');
    const btnClear = document.getElementById('btnClear');

    function updateUI(data) {
        if (data.lastSyncTime) {
            syncDateEl.textContent = data.lastSyncTime;
        }

        if (data.lastSyncCount !== undefined) {
            syncCountEl.textContent = data.lastSyncCount;
        }

        if (data.downloadedMoodleFiles) {
            fileCountEl.textContent = Object.keys(data.downloadedMoodleFiles).length;
        }

        // Gestion de l'état de synchronisation
        if (data.isSyncing) {
            syncStateEl.textContent = 'Synchronisation en cours...';
            statusBox.className = 'status status-pending';
            btnRetry.disabled = true;
            btnRetry.textContent = 'Synchronisation...';
            btnClear.disabled = true;
        } else {
            btnRetry.disabled = false;
            btnRetry.textContent = 'Lancer un tracking Moodle maintenant';
            btnClear.disabled = false;

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
        }
    }

    // Charger l'état initial
    chrome.storage.local.get(null, (data) => {
        updateUI(data);
    });

    // Écouter les changements en temps réel
    chrome.storage.onChanged.addListener((changes, area) => {
        if (area === 'local') {
            chrome.storage.local.get(null, (data) => {
                updateUI(data);
            });
        }
    });

    btnRetry.addEventListener('click', () => {
        chrome.storage.local.get(['moodleSesskey'], (data) => {
            if (data.moodleSesskey) {
                chrome.runtime.sendMessage({ action: "FORCE_BACKGROUND_SYNC" });
            } else {
                alert("Impossible de synchroniser : Ouvre d'abord un onglet Moodle pour capturer ta session !");
            }
        });
    });

    btnClear.addEventListener('click', () => {
        if (confirm("Es-tu sûr de vouloir vider le cache de l'extension ? Toute la mémoire des fichiers téléchargés et événements envoyés sera effacée.")) {
            chrome.runtime.sendMessage({ action: "CLEAR_CACHE" }, (response) => {
                alert("Cache vidé avec succès ! Actualise ta page Moodle et relance le tracking.");
            });
        }
    });
});
