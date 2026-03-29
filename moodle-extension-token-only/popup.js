// NovaFlow Simple Moodle Extension - popup.js

function updateUI() {
    chrome.storage.local.get(['status', 'lastCapturedHost', 'lastCapturedTime'], (data) => {
        if (data.status === "Connecté") {
            const statusEl = document.getElementById('status-text');
            if (statusEl) {
                statusEl.innerText = "Statut : ✅ Session Capturée";
                statusEl.style.color = "#22c55e";
            }
            
            const detailEl = document.getElementById('detail-text');
            if (detailEl) {
                detailEl.innerHTML = `Host: ${data.lastCapturedHost}<br>Dernier passage: ${data.lastCapturedTime}`;
                detailEl.style.display = "block";
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', updateUI);
chrome.storage.onChanged.addListener(updateUI);
