// NovaFlow Moodle Extension - content.js
// Injecté sur les pages Moodle pour extraire les événements via l'API interne

console.log("NovaFlow Moodle Extension content script loaded.");

async function scrapeMoodleEventsAndSync() {
    try {
        console.log("NovaFlow: Recherche de la clé de session Moodle (sesskey)...");
        // 1. Get the session key from the logout link (most reliable way from a content script without injected scripts)
        const logoutLink = document.querySelector('a[href*="logout.php?sesskey="]');
        if (!logoutLink) {
            console.log("NovaFlow: sesskey introuvable. Utilisateur non connecté ou thème non standard.");
            return;
        }
        const sesskey = new URL(logoutLink.href).searchParams.get('sesskey');

        if (!sesskey) {
            console.log("NovaFlow: Impossible d'extraire la sesskey de l'URL.");
            return;
        }

        console.log("NovaFlow: sesskey trouvée, interrogation de l'API Moodle...");

        // 2. Prepare API calls for the current and next month to get all events
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1; // 1-indexed for Moodle

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

        // 3. Fetch from Moodle API (relative URL guarantees domain match)
        const response = await fetch('/lib/ajax/service.php?sesskey=' + sesskey + '&info=core_calendar_get_calendar_monthly_view', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // 4. Extract events from the API responses
        let rawEvents = [];
        data.forEach(responseItem => {
            if (!responseItem.error && responseItem.data && responseItem.data.weeks) {
                responseItem.data.weeks.forEach(week => {
                    if (week.days) {
                        week.days.forEach(day => {
                            if (day.events && day.events.length > 0) {
                                rawEvents.push(...day.events);
                            }
                        });
                    }
                });
            } else if (responseItem.error) {
                console.error("NovaFlow: Erreur API Moodle:", responseItem.exception || responseItem.error);
            }
        });

        // 5. Transform to NovaFlow format
        const extractedEvents = rawEvents.map(ev => {
            // Moodle timestamps are in seconds, JS needs milliseconds
            const eventDate = new Date(ev.timestart * 1000).toISOString();

            // Clean title (remove prefixes like "Devoir doit être rendu" if possible, but keep name)
            const title = ev.name ? ev.name.replace(/(<([^>]+)>)/gi, "") : (ev.activityname || "Événement Moodle");

            // Add a unique ID suffix to avoid react key complaints
            const uid = `moodle_ext_${ev.id || Date.now()}`;

            const host = window.location.hostname;
            const parts = host.split('.');
            const org = parts.length >= 2 ? parts[parts.length - 2] : "Moodle";
            const orgName = org.charAt(0).toUpperCase() + org.slice(1);

            return {
                id: uid,
                title: title.trim(),
                due_date_text: eventDate,
                timestamp: eventDate,
                link: ev.url || window.location.origin,
                course: ev.course && ev.course.fullname ? ev.course.fullname : "Général",
                organization: orgName,
                source_url: window.location.href
            };
        });

        // Deduplicate events (same event might appear multiple times if weeks overlap or ID duplicates)
        const uniqueMap = new Map();
        extractedEvents.forEach(item => {
            uniqueMap.set(item.link + item.title, item);
        });
        const uniqueEvents = Array.from(uniqueMap.values());

        console.log(`NovaFlow a extrait ${uniqueEvents.length} événements via l'API interne Moodle.`);

        if (uniqueEvents.length > 0) {
            console.log("Aperçu des événements:", uniqueEvents.slice(0, 2));
        }

        // 6. Send to background script (using the format expected by the previous background.js, which looks for action "SYNC_MOODLE_EVENTS")
        // Note: the background script expects action: "SYNC_MOODLE_EVENTS" and data: extractedEvents
        chrome.runtime.sendMessage({
            action: "SYNC_MOODLE_EVENTS",
            data: uniqueEvents,
            status: uniqueEvents.length > 0 ? "success" : "empty"
        }, response => {
            if (chrome.runtime.lastError) {
                console.warn("NovaFlow: Erreur d'envoi au background script (extension peut-être désactivée/rechargée):", chrome.runtime.lastError.message);
            } else {
                console.log("NovaFlow: Réponse de background.js:", response);
            }
        });

    } catch (err) {
        console.error("NovaFlow: Erreur critique lors de l'extraction des événements:", err);
    }
}

// Run the script
scrapeMoodleEventsAndSync();

// Relancer l'extraction si l'utilisateur change de mois dans le calendrier / timeline
document.addEventListener('click', (e) => {
    if (e.target.closest('button') || e.target.closest('a')) {
        setTimeout(scrapeMoodleEventsAndSync, 2000);
    }
});
