/**
 * Service Worker en arrière-plan
 * Gère les alarmes silencieuses pour interroger Moodle de manière invisible
 * et synchronise les événements avec NovaFlow.
 */

const NOVAFLOW_URL = "http://localhost:8000/api/moodle/sync";
const ALARM_NAME = "moodleBackgroundSync";
const SYNC_PERIOD_MINUTES = 60; // Sync every hour

let isSyncing = false;

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
    if (isSyncing) {
        console.log("NovaFlow: Synchronisation déjà en cours, ignorée.");
        return;
    }
    isSyncing = true;

    try {
        const ObjectData = await chrome.storage.local.get(['moodleSesskey', 'moodleHost', 'moodleSourceUrl']);
        const { moodleSesskey, moodleHost, moodleSourceUrl } = ObjectData;

        if (!moodleSesskey || !moodleHost) {
            console.log("NovaFlow: Impossible de synchroniser en arrière-plan. Aucune sesskey enregistrée.");
            return;
        }

        try {
            // A. Fetch from Moodle API directly using Chrome's background cookie jar
            const [rawEvents, courses] = await Promise.all([
                fetchMoodleEvents(moodleHost, moodleSesskey, moodleSourceUrl),
                fetchMoodleCourses(moodleHost, moodleSesskey)
            ]);

            if (rawEvents && rawEvents.length > 0) {
                // B. Send parsed events and courses to NovaFlow
                await syncToNovaFlow(rawEvents, courses);
            }

            if (courses && courses.length > 0) {
                // Fetch and download course files
                await fetchAndDownloadCourseFiles(moodleHost, moodleSesskey, courses);
            }
        } catch (error) {
            console.error("NovaFlow: Erreur durant la synchronisation en arrière-plan:", error);
        }
    } finally {
        isSyncing = false;
    }
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

async function fetchMoodleCourses(host, sesskey) {
    try {
        const payload = [{
            index: 0,
            methodname: 'core_course_get_enrolled_courses_by_timeline_classification',
            args: { classification: 'all', limit: 0, offset: 0, sort: 'fullname' }
        }];

        const apiUrl = `${host}/lib/ajax/service.php?sesskey=${sesskey}&info=core_course_get_enrolled_courses_by_timeline_classification`;

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) return [];

        const data = await response.json();
        const coursesData = data[0]?.data?.courses || [];

        return coursesData.map(c => ({
            id: c.id,
            shortname: c.shortname,
            fullname: c.fullname
        }));
    } catch (e) {
        console.error("NovaFlow: Erreur fetching courses", e);
        return [];
    }
}

async function syncToNovaFlow(events, courses = []) {
    try {
        const payload = {
            source: "moodle_extension",
            timestamp: new Date().toISOString(),
            events: events,
            courses: courses
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

async function fetchAndDownloadCourseFiles(host, sesskey, courses) {
    const data = await chrome.storage.local.get(['downloadedMoodleFiles']);
    const downloadedFiles = data.downloadedMoodleFiles || {};

    for (const course of courses) {
        try {
            const payload = [{
                index: 0,
                methodname: 'core_courseformat_get_state',
                args: { courseid: course.id }
            }];

            const apiUrl = `${host}/lib/ajax/service.php?sesskey=${sesskey}&info=core_courseformat_get_state`;

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) continue;

            const responseData = await response.json();
            if (responseData[0]?.error || !responseData[0]?.data) continue;

            let courseFormatData;
            try {
                courseFormatData = JSON.parse(responseData[0].data);
            } catch (e) {
                console.warn("NovaFlow: Erreur de parsing JSON pour le format du cours", e);
                continue;
            }

            const sections = courseFormatData.section || [];
            const cmList = courseFormatData.cm || [];

            const modulesById = {};
            cmList.forEach(cm => { modulesById[cm.id] = cm; });

            for (const section of sections) {
                const cmIds = section.cmlist || [];
                for (const cmId of cmIds) {
                    const cm = modulesById[cmId];
                    if (cm && cm.module === 'resource' && cm.url) {
                        const fileKey = cm.id; // Unique identifier

                        if (!downloadedFiles[fileKey]) {
                            const safeCourseName = (course.shortname || course.fullname || `Course_${course.id}`).replace(/[/\\?%*:|"<>]/g, '-').trim();
                            const safeSectionName = (section.title || `Section_${section.section}`).replace(/[/\\?%*:|"<>]/g, '-').trim();
                            let safeFileName = (cm.name || 'Fichier').replace(/[/\\?\\[\\]%*:|"<>]/g, '-').trim();

                            try {
                                const headRes = await fetch(`${cm.url}&redirect=1`, { method: 'HEAD' });
                                let finalUrl = headRes.url;
                                let extension = '';

                                const contentDisposition = headRes.headers.get('Content-Disposition');
                                if (contentDisposition) {
                                    const matchStar = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
                                    const match = contentDisposition.match(/filename="?([^";]+)"?/i);
                                    let extractedName = '';
                                    if (matchStar) extractedName = decodeURIComponent(matchStar[1]);
                                    else if (match) extractedName = match[1];

                                    if (extractedName.includes('.')) {
                                        extension = '.' + extractedName.split('.').pop();
                                    }
                                }

                                if (!extension) {
                                    const urlObj = new URL(finalUrl);
                                    const pathSegments = urlObj.pathname.split('/');
                                    const lastSegment = decodeURIComponent(pathSegments[pathSegments.length - 1]);
                                    if (lastSegment.includes('.')) {
                                        extension = '.' + lastSegment.split('.').pop();
                                    }
                                }

                                if (!extension) {
                                    const contentType = headRes.headers.get('Content-Type') || '';
                                    if (contentType.includes('application/pdf')) extension = '.pdf';
                                    else if (contentType.includes('application/vnd.openxmlformats-officedocument.wordprocessingml.document')) extension = '.docx';
                                    else if (contentType.includes('application/msword')) extension = '.doc';
                                    else if (contentType.includes('application/vnd.ms-excel')) extension = '.xls';
                                    else if (contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) extension = '.xlsx';
                                    else if (contentType.includes('application/vnd.ms-powerpoint')) extension = '.ppt';
                                    else if (contentType.includes('application/vnd.openxmlformats-officedocument.presentationml.presentation')) extension = '.pptx';
                                    else if (contentType.includes('application/zip')) extension = '.zip';
                                    else if (contentType.includes('text/plain')) extension = '.txt';
                                }

                                extension = extension.toLowerCase();
                                if (extension && safeFileName.toLowerCase().endsWith(extension)) {
                                    safeFileName = safeFileName.slice(0, -extension.length).trim();
                                }

                                const destPath = `NovaFlow_Moodle/${safeCourseName}/${safeSectionName}/${safeFileName}${extension}`;

                                // Mark as downloaded immediately to prevent race conditions causing duplicate downloads
                                downloadedFiles[fileKey] = true;
                                chrome.storage.local.set({ downloadedMoodleFiles: downloadedFiles });

                                chrome.downloads.download({
                                    url: `${cm.url}&redirect=1`,
                                    filename: destPath,
                                    conflictAction: 'overwrite'
                                }, (downloadId) => {
                                    if (chrome.runtime.lastError) {
                                        console.error("NovaFlow: Erreur téléchargement:", chrome.runtime.lastError.message);
                                        // Optionnel: On pourrait revert le set si ça d'échoue
                                    } else {
                                        console.log(`NovaFlow: Fichier en téléchargement -> ${destPath}`);
                                    }
                                });
                            } catch (e) {
                                console.log("NovaFlow: Erreur resolve URL module", fileKey, e);
                            }
                        }
                    }
                }
            }
        } catch (e) {
            console.error(`NovaFlow: Erreur during file fetch for course ${course.id}:`, e);
        }
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
