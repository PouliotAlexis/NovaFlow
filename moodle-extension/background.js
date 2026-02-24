/**
 * Service Worker en arrière-plan
 * Gère les alarmes silencieuses pour interroger Moodle de manière invisible
 * et synchronise les événements avec NovaFlow.
 */

const NOVAFLOW_URL = "http://localhost:8000/api/moodle/sync";
const ALARM_NAME = "moodleBackgroundSync";
const SYNC_PERIOD_MINUTES = 60; // Sync every hour

// 1. Listen for session updates from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "UPDATE_MOODLE_SESSION") {
        const { sesskey, host, url } = request.data;

        chrome.storage.local.set({
            moodleSesskey: sesskey,
            moodleHost: host,
            moodleSourceUrl: url
        }, () => {
            console.log("NovaFlow: Session Moodle mise à jour en arrière-plan.");
            // Trigger an immediate sync when we get a fresh session key
            performBackgroundSync();
        });

        // Setup recurrent alarm if not already existing
        setupAlarm();
    } else if (request.action === "FORCE_BACKGROUND_SYNC") {
        console.log("NovaFlow: Synchronisation forcée depuis le popup.");
        performBackgroundSync();
    }
});

// 2. Setup periodic alarm
function setupAlarm() {
    chrome.alarms.get(ALARM_NAME, (alarm) => {
        if (!alarm) {
            chrome.alarms.create(ALARM_NAME, {
                periodInMinutes: SYNC_PERIOD_MINUTES
            });
            console.log(`NovaFlow: Alarme de synchronisation créée (${SYNC_PERIOD_MINUTES}m).`);
        }
    });
}

// 3. Listen for alarm triggers
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === ALARM_NAME) {
        console.log("NovaFlow: Réveil en arrière-plan, début de la synchronisation Moodle...");
        performBackgroundSync();
    }
});

// 4. Core Logic: Fetch from Moodle API & Send to NovaFlow
async function performBackgroundSync() {
    chrome.storage.local.get(['moodleSesskey', 'moodleHost', 'moodleSourceUrl'], async (data) => {
        const { moodleSesskey, moodleHost, moodleSourceUrl } = data;

        if (!moodleSesskey || !moodleHost) {
            console.log("NovaFlow: Impossible de synchroniser en arrière-plan. Aucune sesskey enregistrée.");
            return;
        }

        try {
            // A. Fetch from Moodle API directly using Chrome's background cookie jar
            const rawEvents = await fetchMoodleEvents(moodleHost, moodleSesskey, moodleSourceUrl);

            if (rawEvents && rawEvents.length > 0) {
                // B. Send parsed events to NovaFlow
                await syncToNovaFlow(rawEvents);
            }
        } catch (error) {
            console.error("NovaFlow: Erreur durant la synchronisation en arrière-plan:", error);
        }
    });
}

async function fetchMoodleEvents(host, sesskey, sourceUrl) {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;

    let nextYear = currentYear;
    let nextMonth = currentMonth + 1;
    if (nextMonth > 12) {
        nextMonth = 1;
        nextYear += 1;
    }

    const payload = [
        {
            index: 0,
            methodname: 'core_calendar_get_calendar_monthly_view',
            args: { year: currentYear, month: currentMonth, courseid: 1, categoryid: 0, includenavigation: false, mini: true }
        },
        {
            index: 1,
            methodname: 'core_calendar_get_calendar_monthly_view',
            args: { year: nextYear, month: nextMonth, courseid: 1, categoryid: 0, includenavigation: false, mini: true }
        }
    ];

    const apiUrl = `${host}/lib/ajax/service.php?sesskey=${sesskey}&info=core_calendar_get_calendar_monthly_view`;

    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    let extractedEvents = [];
    data.forEach(responseItem => {
        if (!responseItem.error && responseItem.data && responseItem.data.weeks) {
            responseItem.data.weeks.forEach(week => {
                if (week.days) {
                    week.days.forEach(day => {
                        if (day.events && day.events.length > 0) {
                            extractedEvents.push(...day.events);
                        }
                    });
                }
            });
        }
    });

    // Transform to NovaFlow format
    const formattedEvents = extractedEvents.map(ev => {
        const eventDate = new Date(ev.timestart * 1000).toISOString();
        const title = ev.name ? ev.name.replace(/(<([^>]+)>)/gi, "") : (ev.activityname || "Événement Moodle");
        const uid = `moodle_ext_${ev.id || Date.now()}`;

        let org = "Moodle";
        try {
            const parts = new URL(host).hostname.split('.');
            org = parts.length >= 2 ? parts[parts.length - 2] : "Moodle";
            org = org.charAt(0).toUpperCase() + org.slice(1);
        } catch (e) { }

        return {
            id: uid,
            title: title.trim(),
            due_date_text: eventDate,
            timestamp: eventDate,
            link: ev.url || host,
            course: ev.course && ev.course.fullname ? ev.course.fullname : "Général",
            organization: org,
            source_url: sourceUrl || host
        };
    });

    // Deduplicate
    const uniqueMap = new Map();
    formattedEvents.forEach(item => uniqueMap.set(item.link + item.title, item));
    return Array.from(uniqueMap.values());
}

async function syncToNovaFlow(events) {
    try {
        const payload = {
            source: "moodle_extension",
            timestamp: new Date().toISOString(),
            events: events
        };

        const response = await fetch(NOVAFLOW_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            console.log(`NovaFlow: Synchronisation réussie de ${events.length} événements.`);
            updateBadgeStatus("OK", "#22c55e"); // Vert
            chrome.storage.local.set({
                lastSyncTime: new Date().toLocaleString(),
                lastSyncCount: events.length,
                syncStatus: "success"
            });
        } else {
            console.warn("NovaFlow: Le serveur a retourné une erreur :", response.status);
            handleSyncFailure(events);
        }

    } catch (error) {
        console.warn("NovaFlow: Impossible de joindre le serveur. Serveur fermé ?");
        handleSyncFailure(events);
    }
}

function handleSyncFailure(events) {
    updateBadgeStatus("ERR", "#ef4444"); // Rouge
    chrome.storage.local.set({
        queuedEvents: events,
        lastSyncTime: new Date().toLocaleString(),
        syncStatus: "failed"
    });
}

function updateBadgeStatus(text, color) {
    chrome.action.setBadgeText({ text: text });
    chrome.action.setBadgeBackgroundColor({ color: color });
    setTimeout(() => {
        chrome.action.setBadgeText({ text: "" });
    }, 5000);
}

// On startup, setup alarm just in case
chrome.runtime.onStartup.addListener(setupAlarm);
chrome.runtime.onInstalled.addListener(setupAlarm);
