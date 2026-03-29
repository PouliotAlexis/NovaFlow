// NovaFlow Simple Moodle Extension - popup.js

function updateUI() {
    chrome.storage.local.get(['status', 'lastCapturedHost', 'lastCapturedTime', 'hasToken', 'hasSesskey'], (data) => {
        const statusEl = document.getElementById('status-text');
        const detailEl = document.getElementById('detail-text');

        if (data.status === "Connecté") {
            statusEl.innerText = "Statut : ✅ Session Capturée";
            statusEl.style.color = "#22c55e";
            
            let type = data.hasToken ? "Jeton REST (Complet)" : "Sesskey (Partiel)";
            detailEl.innerHTML = `<b>${type}</b><br>Host: ${data.lastCapturedHost}<br>Dernage passage: ${data.lastCapturedTime}`;
            detailEl.style.display = "block";
        } else {
            statusEl.innerText = "Statut : ⏳ En attente...";
            statusEl.style.color = "#94a3b8";
        }
    });
}

document.addEventListener('DOMContentLoaded', updateUI);
chrome.storage.onChanged.addListener(updateUI);

// Ajouter un bouton de test
const btn = document.createElement('button');
btn.innerText = "Réessayer la capture";
btn.style = "width:100%; margin-top:10px; padding:5px; font-size:10px; cursor:pointer;";
btn.onclick = () => {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        chrome.scripting.executeScript({
            target: {tabId: tabs[0].id},
            func: () => { window.location.reload(); }
        });
    });
};
document.body.appendChild(btn);
