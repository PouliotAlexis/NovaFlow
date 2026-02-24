"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Task {
    id: string;
    title: string;
    meta: string;
    priority: "high" | "medium" | "low";
    done: boolean;
    parent_event_id?: string;
}

interface CalendarEvent {
    id: string;
    title: string;
    date: string;
    end_date?: string;
    time: string;
    end_time?: string;
    type: "exam" | "deadline" | "meeting" | "personal";
    priority: "high" | "medium" | "low";
    location?: string;
    all_day?: boolean;
    link?: string;
    accounts?: string[];
    source?: string;
    category?: string;
    done?: boolean;
    tasks: Task[];
}

const EVENT_COLORS: Record<string, { bg: string; text: string; label: string }> = {
    exam: { bg: "rgba(239, 68, 68, 0.15)", text: "var(--nf-danger)", label: "Examen" },
    deadline: { bg: "rgba(245, 158, 11, 0.15)", text: "var(--nf-warning)", label: "Échéance" },
    meeting: { bg: "rgba(59, 130, 246, 0.15)", text: "var(--nf-info)", label: "Réunion" },
    personal: { bg: "rgba(34, 197, 94, 0.15)", text: "var(--nf-success)", label: "Personnel" },
};

const DAYS_FR = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];
const MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

function getDaysInMonth(year: number, month: number) {
    return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number) {
    return new Date(year, month, 1).getDay();
}

function guessEventType(title: string): "exam" | "deadline" | "meeting" | "personal" {
    const lower = title.toLowerCase();
    if (lower.includes("exam") || lower.includes("intra") || lower.includes("final") || lower.includes("quiz") || lower.includes("test")) return "exam";
    if (lower.includes("remise") || lower.includes("deadline") || lower.includes("date limite") || lower.includes("tp") || lower.includes("devoir") || lower.includes("doit être rendu")) return "deadline";
    if (lower.includes("réunion") || lower.includes("meeting") || lower.includes("rencontre") || lower.includes("équipe")) return "meeting";
    return "personal";
}

function parseUnifiedEvent(event: any): CalendarEvent {
    const startDate = event.start.split("T")[0];
    let endDate = event.end ? event.end.split("T")[0] : startDate;

    // For all-day events, the 'end' date is typically the start of the next day (exclusive).
    // We adjust it back by one day so a single all-day event doesn't show as a multi-day event.
    if (event.all_day && event.end && endDate !== startDate) {
        const d = new Date(event.end);
        d.setDate(d.getDate() - 1);
        endDate = d.toISOString().split("T")[0];
    }

    const startTime = event.all_day ? "Journée" : new Date(event.start).toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
    const endTime = event.all_day ? "" : new Date(event.end).toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
    const type = guessEventType(event.title);

    return {
        id: event.id,
        title: event.title,
        date: startDate,
        end_date: endDate !== startDate ? endDate : undefined,
        time: startTime,
        end_time: endTime,
        type,
        priority: type === "exam" ? "high" : type === "deadline" ? "high" : "medium",
        location: event.location,
        all_day: event.all_day,
        link: event.link,
        accounts: event.accounts,
        source: event.source,
        category: event.category,
        done: false,
        tasks: event.tasks || []
    };
}

export default function CalendarView({ onNavigate }: { onNavigate?: (view: string) => void }) {
    const today = new Date();
    const [currentMonth, setCurrentMonth] = useState(today.getMonth());
    const [currentYear, setCurrentYear] = useState(today.getFullYear());
    const [selectedDate, setSelectedDate] = useState<string | null>(null);
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [googleAccounts, setGoogleAccounts] = useState<string[]>([]);
    const [microsoftAccounts, setMicrosoftAccounts] = useState<string[]>([]);
    const [moodleUrls, setMoodleUrls] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showAccountsDropdown, setShowAccountsDropdown] = useState(false);

    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);

    // Vérifier les comptes connectés (Google + Microsoft)
    const checkConnection = useCallback(async () => {
        let hasAny = false;
        try {
            const res = await fetch(`${API_URL}/api/auth/google/accounts`);
            if (res.ok) {
                const data = await res.json();
                setGoogleAccounts(data.accounts || []);
                if ((data.accounts || []).length > 0) hasAny = true;
            }
        } catch { }
        try {
            const res = await fetch(`${API_URL}/api/auth/microsoft/accounts`);
            if (res.ok) {
                const data = await res.json();
                setMicrosoftAccounts(data.accounts || []);
                if ((data.accounts || []).length > 0) hasAny = true;
            }
        } catch { }
        try {
            const res = await fetch(`${API_URL}/api/settings/moodle`);
            if (res.ok) {
                const data = await res.json();
                const urls = data.urls || (data.url ? [data.url] : []);
                setMoodleUrls(urls);
                if (urls.length > 0) hasAny = true;
            }
        } catch { }
        return hasAny;
    }, []);

    // Récupérer les événements + statuts de soumission
    const fetchEvents = useCallback(async () => {
        try {
            const [eventsRes, statusRes] = await Promise.all([
                fetch(`${API_URL}/api/calendar/events?days=30`),
                fetch(`${API_URL}/api/calendar/event-status`)
            ]);
            if (!eventsRes.ok) return;
            const data = await eventsRes.json();
            const statusData = statusRes.ok ? await statusRes.json() : {};
            const parsed = (data.events || []).map((e: any) => {
                const evt = parseUnifiedEvent(e);
                evt.done = !!statusData[evt.id];
                return evt;
            });
            setEvents(parsed);
        } catch {
            console.error("Erreur récupération événements");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        const init = async () => {
            const connected = await checkConnection();
            if (connected) {
                await fetchEvents();
            } else {
                setIsLoading(false);
            }
        };
        init();

        // Écouter les changements de tâches depuis d'autres composants (ex: TaskList)
        const handleExternalChange = () => fetchEvents();
        window.addEventListener("novaflow-task-changed", handleExternalChange);

        // Re-fetch quand un job d'automation se termine (ex: Analyse Calendrier)
        window.addEventListener("novaflow-automation-done", handleExternalChange);

        // Re-check connexion + events quand un compte est ajouté/supprimé
        const handleAccountChange = async () => {
            const connected = await checkConnection();
            if (connected) {
                await fetchEvents();
            }
        };
        window.addEventListener("novaflow-account-changed", handleAccountChange);

        // Polling : re-fetch les événements toutes les 60s pour capter les modifications Outlook/Google
        const pollInterval = setInterval(() => {
            fetchEvents();
        }, 60_000);

        return () => {
            window.removeEventListener("novaflow-task-changed", handleExternalChange);
            window.removeEventListener("novaflow-automation-done", handleExternalChange);
            window.removeEventListener("novaflow-account-changed", handleAccountChange);
            clearInterval(pollInterval);
        };
    }, [checkConnection, fetchEvents]);

    // Vérifier le paramètre URL (retour de OAuth)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("google_connected") === "true") {
            checkConnection();
            fetchEvents();
            // Nettoyer l'URL
            window.history.replaceState({}, "", window.location.pathname);
        }
    }, [fetchEvents]);

    const handleConnect = async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/google/login`);
            const data = await res.json();
            if (data.url) {
                window.location.href = data.url;
            }
        } catch {
            console.error("Erreur connexion Google");
        }
    };

    // Déconnexion gérée uniquement via les réglages maintenant
    const handleDisconnect = () => { };

    const toggleTask = async (taskId: string, eventId: string) => {
        // Optimistic update locally
        setEvents(prev => prev.map(evt => {
            if (evt.id === eventId) {
                return {
                    ...evt,
                    tasks: evt.tasks.map(t => t.id === taskId ? { ...t, done: !t.done } : t)
                };
            }
            return evt;
        }));

        try {
            await fetch(`${API_URL}/api/tasks/${taskId}/toggle`, { method: "PATCH" });
            window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
        } catch (error) {
            console.error("Erreur toggle tâche:", error);
            fetchEvents();
        }
    };

    const toggleEventDone = async (eventId: string) => {
        setEvents(prev => prev.map(evt =>
            evt.id === eventId ? { ...evt, done: !evt.done } : evt
        ));
        try {
            await fetch(`${API_URL}/api/calendar/events/${encodeURIComponent(eventId)}/toggle`, { method: "PATCH" });
        } catch (error) {
            console.error("Erreur toggle event:", error);
            fetchEvents();
        }
    };

    const prevMonth = () => {
        if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(currentYear - 1); }
        else { setCurrentMonth(currentMonth - 1); }
    };

    const nextMonth = () => {
        if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(currentYear + 1); }
        else { setCurrentMonth(currentMonth + 1); }
    };

    const formatDate = (day: number) =>
        `${currentYear}-${String(currentMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

    const getEventsForDate = (dateStr: string) => events.filter((e) => {
        if (e.date === dateStr) return true;
        if (e.end_date && dateStr >= e.date && dateStr <= e.end_date) return true;
        return false;
    });

    const isToday = (day: number) =>
        day === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear();

    const upcomingEvents = events
        .filter((e) => {
            const eventDate = new Date(e.date);
            const diff = (eventDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24);
            if (diff >= -1 && diff <= 14) return true;
            // Include multi-day events that span into the visible range
            if (e.end_date) {
                const endDate = new Date(e.end_date);
                const todayStr = today.toISOString().split("T")[0];
                if (todayStr >= e.date && todayStr <= e.end_date) return true;
            }
            return false;
        })
        .sort((a, b) => a.date.localeCompare(b.date));

    const selectedEvents = selectedDate ? getEventsForDate(selectedDate) : [];

    // Si aucun compte connecté, on affiche quand même le calendrier (grid vide)
    // Le bouton de connexion est maintenant dans le header


    return (
        <div className="nf-animate-in" style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "20px" }}>
            {/* Calendar Grid */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">📅 {MONTHS_FR[currentMonth]} {currentYear}</span>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        {(googleAccounts.length + microsoftAccounts.length + moodleUrls.length) > 0 ? (
                            <div style={{ position: "relative" }}>
                                <span
                                    className="nf-card__badge nf-card__badge--success"
                                    style={{ cursor: "pointer", userSelect: "none" }}
                                    onClick={() => setShowAccountsDropdown(!showAccountsDropdown)}
                                >
                                    ✅ {googleAccounts.length + microsoftAccounts.length + moodleUrls.length} compte{(googleAccounts.length + microsoftAccounts.length + moodleUrls.length) > 1 ? "s" : ""} connecté{(googleAccounts.length + microsoftAccounts.length + moodleUrls.length) > 1 ? "s" : ""}
                                </span>
                                {showAccountsDropdown && (
                                    <div className="nf-card nf-animate-in" style={{
                                        position: "absolute",
                                        top: "100%",
                                        right: 0,
                                        marginTop: "8px",
                                        width: "280px",
                                        zIndex: 1000,
                                        padding: "12px",
                                        boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
                                        background: "var(--nf-bg-secondary)",
                                        border: "1px solid var(--nf-border)"
                                    }}>
                                        <h4 style={{ fontSize: "13px", fontWeight: 600, marginBottom: "10px" }}>Calendriers connectés</h4>
                                        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                                            {googleAccounts.map((email) => (
                                                <li key={email} style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: "8px",
                                                    padding: "6px 0",
                                                    borderBottom: "1px solid var(--nf-border-dim)",
                                                    fontSize: "12px"
                                                }}>
                                                    <span style={{ width: "16px", height: "16px", display: "inline-flex" }}><svg viewBox="0 0 24 24" width="16" height="16"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" /></svg></span>
                                                    <span style={{ color: "var(--nf-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{email}</span>
                                                </li>
                                            ))}
                                            {microsoftAccounts.map((email) => (
                                                <li key={email} style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: "8px",
                                                    padding: "6px 0",
                                                    borderBottom: "1px solid var(--nf-border-dim)",
                                                    fontSize: "12px"
                                                }}>
                                                    <span style={{ width: "16px", height: "16px", display: "inline-flex" }}><svg viewBox="0 0 24 24" width="16" height="16"><rect x="1" y="1" width="10" height="10" fill="#F25022" /><rect x="13" y="1" width="10" height="10" fill="#7FBA00" /><rect x="1" y="13" width="10" height="10" fill="#00A4EF" /><rect x="13" y="13" width="10" height="10" fill="#FFB900" /></svg></span>
                                                    <span style={{ color: "var(--nf-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{email}</span>
                                                </li>
                                            ))}
                                            {moodleUrls.map((mUrl, i) => {
                                                let label = "Moodle";
                                                try {
                                                    const host = new URL(mUrl).hostname;
                                                    const parts = host.split(".");
                                                    if (parts.length >= 2) label = parts[parts.length - 2];
                                                    label = label.charAt(0).toUpperCase() + label.slice(1);
                                                } catch { }
                                                return (
                                                    <li key={i} style={{
                                                        display: "flex",
                                                        alignItems: "center",
                                                        gap: "8px",
                                                        padding: "6px 0",
                                                        borderBottom: "1px solid var(--nf-border-dim)",
                                                        fontSize: "12px"
                                                    }}>
                                                        <span style={{ width: "16px", height: "16px", display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: "3px", background: "#f98012", color: "#fff", fontSize: "11px", fontWeight: 700 }}>M</span>
                                                        <span style={{ color: "var(--nf-text)" }}>Moodle — {label}</span>
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                        <button
                                            className="nf-btn nf-btn--ghost"
                                            onClick={() => {
                                                setShowAccountsDropdown(false);
                                                if (onNavigate) onNavigate("settings");
                                            }}
                                            style={{ marginTop: "10px", fontSize: "11px", width: "100%", padding: "6px", textAlign: "center" }}
                                        >
                                            ⚙️ Gérer les comptes
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <button
                                className="nf-btn nf-btn--primary"
                                onClick={() => {
                                    if (onNavigate) {
                                        onNavigate("settings");
                                        window.location.hash = "connections";
                                    }
                                }}
                                style={{ padding: "6px 12px", fontSize: "12px", gap: "6px", display: "inline-flex", alignItems: "center", height: "32px" }}
                            >
                                <span>🔗</span> Connecter
                            </button>
                        )}
                        <button className="nf-btn--icon" onClick={prevMonth}>◀</button>
                        <button className="nf-btn--icon" onClick={nextMonth}>▶</button>
                    </div>
                </div>

                {/* Day Headers */}
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(7, 1fr)",
                    gap: "2px",
                    marginBottom: "8px",
                }}>
                    {DAYS_FR.map((day) => (
                        <div key={day} style={{
                            textAlign: "center",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: "var(--nf-text-muted)",
                            padding: "8px 0",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                        }}>
                            {day}
                        </div>
                    ))}
                </div>

                {/* Calendar Days */}
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(7, 1fr)",
                    gap: "2px",
                }}>
                    {Array.from({ length: firstDay }, (_, i) => (
                        <div key={`empty-${i}`} style={{ padding: "10px" }} />
                    ))}

                    {Array.from({ length: daysInMonth }, (_, i) => {
                        const day = i + 1;
                        const dateStr = formatDate(day);
                        const dayEvents = getEventsForDate(dateStr);
                        const isTodayDay = isToday(day);
                        const isSelected = selectedDate === dateStr;

                        return (
                            <div
                                key={day}
                                onClick={() => setSelectedDate(dateStr)}
                                style={{
                                    padding: "8px",
                                    borderRadius: "var(--nf-radius-sm)",
                                    cursor: "pointer",
                                    textAlign: "center",
                                    background: isSelected
                                        ? "var(--nf-accent-glow)"
                                        : isTodayDay
                                            ? "var(--nf-bg-tertiary)"
                                            : "transparent",
                                    border: isSelected
                                        ? "1px solid var(--nf-accent)"
                                        : isTodayDay
                                            ? "1px solid var(--nf-border-active)"
                                            : "1px solid transparent",
                                    transition: "all var(--nf-transition)",
                                    minHeight: "60px",
                                }}
                            >
                                <div style={{
                                    fontSize: "14px",
                                    fontWeight: isTodayDay ? 700 : 400,
                                    color: isTodayDay ? "var(--nf-accent)" : "var(--nf-text)",
                                    marginBottom: "4px",
                                }}>
                                    {day}
                                </div>

                                <div style={{ display: "flex", justifyContent: "center", gap: "3px", flexWrap: "wrap" }}>
                                    {dayEvents.map((evt) => (
                                        <div
                                            key={evt.id}
                                            style={{
                                                width: "6px",
                                                height: "6px",
                                                borderRadius: "50%",
                                                background: EVENT_COLORS[evt.type]?.text || "var(--nf-text-muted)",
                                            }}
                                        />
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Legend */}
                <div style={{
                    display: "flex",
                    gap: "16px",
                    marginTop: "16px",
                    paddingTop: "16px",
                    borderTop: "1px solid var(--nf-border)",
                }}>
                    {Object.entries(EVENT_COLORS).map(([key, val]) => (
                        <div key={key} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--nf-text-muted)" }}>
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: val.text }} />
                            {val.label}
                        </div>
                    ))}
                </div>
            </div>

            {/* Sidebar */}
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                {/* Selected Date Events */}
                {selectedDate && (
                    <div className="nf-card">
                        <div className="nf-card__header">
                            <span className="nf-card__title">
                                📌 {new Date(selectedDate + "T00:00:00").toLocaleDateString("fr-CA", {
                                    weekday: "long",
                                    day: "numeric",
                                    month: "long",
                                })}
                            </span>
                        </div>
                        {selectedEvents.length > 0 ? (
                            <div className="nf-task-list">
                                {selectedEvents.map((evt) => (
                                    <React.Fragment key={evt.id}>
                                        <div
                                            className="nf-task"
                                            style={{
                                                cursor: evt.link ? "pointer" : "default",
                                                opacity: evt.done ? 0.5 : 1,
                                            }}
                                            onClick={() => evt.link && window.open(evt.link, "_blank")}
                                        >
                                            <div style={{
                                                width: "4px",
                                                height: "100%",
                                                minHeight: "36px",
                                                borderRadius: "2px",
                                                background: EVENT_COLORS[evt.type]?.text || "var(--nf-text-muted)",
                                            }} />
                                            <div className="nf-task__content">
                                                <div className="nf-task__title" style={{
                                                    textDecoration: evt.done ? "line-through" : "none",
                                                }}>{evt.title}</div>
                                                <div className="nf-task__meta">
                                                    {evt.end_date ? (
                                                        <>
                                                            {new Date(evt.date + "T00:00").toLocaleDateString("fr-CA", { day: "numeric", month: "short" })}
                                                            {evt.time !== "Journée" ? ` ${evt.time}` : ""}
                                                            {" → "}
                                                            {new Date(evt.end_date + "T00:00").toLocaleDateString("fr-CA", { day: "numeric", month: "short" })}
                                                            {evt.end_time && evt.end_time !== evt.time ? ` ${evt.end_time}` : ""}
                                                        </>
                                                    ) : (
                                                        <>{evt.time}{evt.end_time && evt.end_time !== evt.time ? ` → ${evt.end_time}` : ""}</>
                                                    )}
                                                    {evt.location ? ` · 📍 ${evt.location}` : ""}
                                                </div>
                                                {evt.category && evt.category !== "Événements de site" && (
                                                    <div style={{ fontSize: "11px", color: "var(--nf-accent)", marginTop: "2px" }}>
                                                        📚 {evt.category}
                                                    </div>
                                                )}
                                                {evt.accounts && (
                                                    <div style={{ fontSize: "10px", color: "var(--nf-text-muted)", marginTop: "4px" }}>
                                                        👤 {evt.accounts.join(" · ")}
                                                    </div>
                                                )}
                                            </div>
                                            {evt.source?.includes("moodle") && evt.title.toLowerCase().includes("doit être rendu") && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); toggleEventDone(evt.id); }}
                                                    style={{
                                                        padding: "4px 10px",
                                                        fontSize: "11px",
                                                        fontWeight: 600,
                                                        borderRadius: "6px",
                                                        border: "none",
                                                        cursor: "pointer",
                                                        whiteSpace: "nowrap",
                                                        background: evt.done ? "rgba(34, 197, 94, 0.2)" : "rgba(124, 92, 252, 0.15)",
                                                        color: evt.done ? "var(--nf-success)" : "var(--nf-accent)",
                                                        transition: "all 0.2s ease",
                                                    }}
                                                >
                                                    {evt.done ? "Remis ✓" : "Marquer remis"}
                                                </button>
                                            )}
                                            {!evt.source?.includes("moodle") && (
                                                <div className={`nf-task__priority nf-task__priority--${evt.priority}`} />
                                            )}
                                        </div>

                                        {evt.tasks && evt.tasks.length > 0 && (
                                            <div style={{ paddingLeft: "24px", display: "flex", flexDirection: "column", gap: "4px", marginTop: "-8px", marginBottom: "8px" }}>
                                                {evt.tasks.map(task => (
                                                    <div
                                                        key={task.id}
                                                        className="nf-task"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            toggleTask(task.id, evt.id);
                                                        }}
                                                        style={{ minHeight: "32px", padding: "4px 8px", background: "rgba(255,255,255,0.02)" }}
                                                    >
                                                        <div className={`nf-task__checkbox ${task.done ? "nf-task__checkbox--checked" : ""}`} style={{ width: "14px", height: "14px", fontSize: "10px" }}>
                                                            {task.done && "✓"}
                                                        </div>
                                                        <div className="nf-task__content">
                                                            <div className={`nf-task__title ${task.done ? "nf-task__title--done" : ""}`} style={{ fontSize: "12px" }}>
                                                                {task.title}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </React.Fragment>
                                ))}
                            </div>
                        ) : (
                            <p style={{ color: "var(--nf-text-muted)", fontSize: "13px", textAlign: "center", padding: "16px" }}>
                                Aucun événement ce jour
                            </p>
                        )}
                    </div>
                )}

                {/* Upcoming Events */}
                <div className="nf-card">
                    <div className="nf-card__header">
                        <span className="nf-card__title">⏰ Prochains événements</span>
                        <span className="nf-card__badge nf-card__badge--warning">{upcomingEvents.length}</span>
                    </div>
                    {isLoading ? (
                        <p style={{ color: "var(--nf-text-muted)", fontSize: "13px", textAlign: "center", padding: "16px" }}>
                            Chargement...
                        </p>
                    ) : upcomingEvents.length > 0 ? (
                        <div className="nf-task-list">
                            {upcomingEvents.map((evt) => {
                                const eventDate = new Date(evt.date + "T00:00:00");
                                const diff = Math.ceil((eventDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                                const relativeDay = diff <= 0 ? "Aujourd'hui" : diff === 1 ? "Demain" : `Dans ${diff}j`;

                                return (
                                    <div
                                        key={evt.id}
                                        className="nf-task"
                                        style={{ cursor: evt.link ? "pointer" : "default" }}
                                        onClick={() => evt.link && window.open(evt.link, "_blank")}
                                    >
                                        <div style={{
                                            width: "4px",
                                            height: "100%",
                                            minHeight: "36px",
                                            borderRadius: "2px",
                                            background: EVENT_COLORS[evt.type]?.text || "var(--nf-text-muted)",
                                            marginRight: "8px"
                                        }} />
                                        <span style={{
                                            padding: "4px 8px",
                                            borderRadius: "6px",
                                            fontSize: "11px",
                                            fontWeight: 700,
                                            background: EVENT_COLORS[evt.type]?.bg || "var(--nf-bg-tertiary)",
                                            color: EVENT_COLORS[evt.type]?.text || "var(--nf-text-muted)",
                                            whiteSpace: "nowrap",
                                            marginRight: "8px"
                                        }}>
                                            {relativeDay}
                                        </span>
                                        <div className="nf-task__content">
                                            <div className="nf-task__title">{evt.title}</div>
                                            <div className="nf-task__meta">
                                                {evt.time}
                                                {evt.location ? ` · 📍 ${evt.location}` : ""}
                                            </div>
                                            {evt.accounts && (
                                                <div style={{ fontSize: "10px", color: "var(--nf-text-muted)", marginTop: "2px" }}>
                                                    👤 {evt.accounts.map(email => email.split("@")[0]).join(" · ")}
                                                </div>
                                            )}
                                        </div>
                                        <div className={`nf-task__priority nf-task__priority--${evt.priority}`} />
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <p style={{ color: "var(--nf-text-muted)", fontSize: "13px", textAlign: "center", padding: "16px" }}>
                            {(googleAccounts.length + microsoftAccounts.length) > 0 ? "Aucun événement à venir" : "Connecte un calendrier pour voir tes événements"}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
