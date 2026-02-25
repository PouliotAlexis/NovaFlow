/**
 * Service Worker en arrière-plan
 * Gère les alarmes silencieuses pour interroger Moodle de manière invisible
 * et synchronise les événements avec NovaFlow.
 */

const NOVAFLOW_URL = "http://localhost:8000/api/moodle/sync";
const ALARM_NAME = "moodleBackgroundSync";
const SYNC_PERIOD_MINUTES = 60; // Sync every hour
const CONCURRENCY_LIMIT = 5; // Nombre maximum de requêtes simultanées pour les fichiers

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
    const statusData = await chrome.storage.local.get(['isSyncing']);
    if (statusData.isSyncing) {
        console.log("NovaFlow: Synchronisation déjà en cours (état stocké), ignorée.");
        return;
    }

    isSyncing = true;
    await chrome.storage.local.set({ isSyncing: true });

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

            let newFilesTracker = [];
            if (courses && courses.length > 0) {
                // Fetch and download course files
                newFilesTracker = await fetchAndDownloadCourseFiles(moodleHost, moodleSesskey, courses);
            }

            if (rawEvents && rawEvents.length > 0 || newFilesTracker.length > 0) {
                // B. Send parsed events and courses to NovaFlow
                await syncToNovaFlow(rawEvents, courses, newFilesTracker);
            }
        } catch (error) {
            console.error("NovaFlow: Erreur durant la synchronisation en arrière-plan:", error);
        }
    } finally {
        isSyncing = false;
        await chrome.storage.local.set({ isSyncing: false });
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

async function syncToNovaFlow(events, courses = [], downloadedFiles = []) {
    try {
        const payload = {
            source: "moodle_extension",
            timestamp: new Date().toISOString(),
            events: events,
            courses: courses,
            downloaded_files: downloadedFiles
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
    let newlyTriggeredFilesCount = 0;
    let newlyTriggeredPaths = [];

    console.log(`NovaFlow: Début de l'extraction des fichiers pour ${courses.length} cours.`);

    const fetchCourseState = async (course) => {
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

            if (!response.ok) return null;
            const responseData = await response.json();
            if (responseData[0]?.error || !responseData[0]?.data) return null;

            let courseFormatData;
            try {
                courseFormatData = JSON.parse(responseData[0].data);
            } catch (e) {
                console.warn("NovaFlow: Erreur parsing JSON cours", e);
                return null;
            }
            return { course, courseFormatData };
        } catch (e) {
            console.warn(`NovaFlow: Erreur état cours ${course.id}:`, e);
            return null;
        }
    };

    // 1. Récupérer les états de tous les cours en parallèle
    const courseStatesPromises = courses.map(fetchCourseState);
    const courseResults = await Promise.all(courseStatesPromises);
    const validCourseResults = courseResults.filter(r => r !== null);

    // 2. Extraire la liste de tous les fichiers à vérifier
    const allFileTasks = [];
    for (const { course, courseFormatData } of validCourseResults) {
        const sections = courseFormatData.section || [];
        const cmList = courseFormatData.cm || [];
        const modulesById = {};
        cmList.forEach(cm => { modulesById[cm.id] = cm; });

        for (const section of sections) {
            const cmIds = section.cmlist || [];
            for (const cmId of cmIds) {
                const cm = modulesById[cmId];
                if (cm && cm.module === 'resource' && cm.url) {
                    const fileKey = cm.id; // L'ID du module ressource
                    if (!downloadedFiles[fileKey]) {
                        allFileTasks.push({ course, section, cm, fileKey });
                    }
                }
            }
        }
    }

    console.log(`NovaFlow: ${allFileTasks.length} nouveaux fichiers potentiels détectés.`);

    // 3. Traiter les fichiers avec une limite de confluence
    const processFile = async ({ course, section, cm, fileKey }) => {
        try {
            const safeCourseName = (course.shortname || course.fullname || `Course_${course.id}`).replace(/[/\\?%*:|"<>]/g, '-').trim();
            const safeSectionName = (section.title || `Section_${section.section}`).replace(/[/\\?%*:|"<>]/g, '-').trim();
            let safeFileName = (cm.name || 'Fichier').replace(/[/\\?\\[\\]%*:|"<>]/g, '-').trim();

            let headRes;
            try {
                // Moodle a parfois des URL invalides générant une erreur fatale dans fetch
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 secondes max pour les requêtes HEAD
                headRes = await fetch(`${cm.url}&redirect=1`, { method: 'HEAD', signal: controller.signal });
                clearTimeout(timeoutId);
            } catch (err) {
                console.warn(`NovaFlow: Fetch HEAD échoué ou expiré pour ${safeFileName}:`, err);
                return null;
            }

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
                try {
                    const urlObj = new URL(finalUrl);
                    const pathSegments = urlObj.pathname.split('/');
                    const lastSegment = decodeURIComponent(pathSegments[pathSegments.length - 1]);
                    if (lastSegment.includes('.')) {
                        extension = '.' + lastSegment.split('.').pop();
                    }
                } catch (e) { }
            }

            if (!extension) {
                const contentType = headRes.headers.get('Content-Type') || '';
                const mimeMap = {
                    'application/pdf': '.pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'application/msword': '.doc',
                    'application/vnd.ms-excel': '.xls',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                    'application/vnd.ms-powerpoint': '.ppt',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
                    'application/zip': '.zip',
                    'text/plain': '.txt'
                };
                for (const [mime, ext] of Object.entries(mimeMap)) {
                    if (contentType.includes(mime)) {
                        extension = ext;
                        break;
                    }
                }
            }

            extension = extension.toLowerCase();
            if (extension && safeFileName.toLowerCase().endsWith(extension)) {
                safeFileName = safeFileName.slice(0, -extension.length).trim();
            }

            const destPath = `NovaFlow_Moodle/${safeCourseName}/${safeSectionName}/${safeFileName}${extension}`;

            return new Promise((resolve) => {
                // Timeout au cas où chrome.downloads se coince silencieusement au lancement
                let downloadTimeout = setTimeout(() => {
                    console.warn(`NovaFlow: Timeout lors de l'appel initial à chrome.downloads pour ${safeFileName}`);
                    resolve(null);
                }, 5000);

                chrome.downloads.download({
                    url: `${cm.url}&redirect=1`,
                    filename: destPath,
                    conflictAction: 'overwrite',
                    saveAs: false
                }, (downloadId) => {
                    clearTimeout(downloadTimeout);
                    if (chrome.runtime.lastError || !downloadId) {
                        console.error(`NovaFlow: Erreur download ${safeFileName}:`, chrome.runtime.lastError?.message);
                        resolve(null);
                    } else {
                        console.log(`NovaFlow: Téléchargement lancé id=${downloadId} -> ${destPath}`);
                        downloadedFiles[fileKey] = true;
                        newlyTriggeredFilesCount++;
                        newlyTriggeredPaths.push(destPath);
                        resolve(destPath);
                    }
                });
            });
        } catch (e) {
            console.warn("NovaFlow: Erreur inattendue traitement fichier", fileKey, e);
            return null;
        }
    };

    // Exécution par lots (batches) pour respecter CONCURRENCY_LIMIT
    for (let i = 0; i < allFileTasks.length; i += CONCURRENCY_LIMIT) {
        const batch = allFileTasks.slice(i, i + CONCURRENCY_LIMIT);
        console.log(`NovaFlow: Démarrage lot de fichiers ${i} à ${i + batch.length} sur ${allFileTasks.length} total.`);
        await Promise.all(batch.map(processFile));

        // Sauvegarder l'état régulièrement après chaque lot
        await chrome.storage.local.set({ downloadedMoodleFiles: downloadedFiles });
        console.log(`NovaFlow: Progression extraction: lot terminé (${Math.min(i + CONCURRENCY_LIMIT, allFileTasks.length)}/${allFileTasks.length})`);
    }

    console.log(`NovaFlow: Extraction terminée. ${newlyTriggeredFilesCount} fichiers ajoutés.`);
    return newlyTriggeredPaths;
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

// On startup, setup alarm and reset syncing state in case of crash
chrome.runtime.onStartup.addListener(() => {
    chrome.storage.local.set({ isSyncing: false });
    setupAlarm();
});

chrome.runtime.onInstalled.addListener(() => {
    chrome.storage.local.set({ isSyncing: false });
    setupAlarm();
});
