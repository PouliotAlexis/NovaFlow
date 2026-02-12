"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CalendarEvent {
    id: string;
    title: string;
    date: string;
    time: string;
    end_time?: string;
    type: "exam" | "deadline" | "meeting" | "personal";
    priority: "high" | "medium" | "low";
    location?: string;
    all_day?: boolean;
    link?: string;
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
    if (lower.includes("remise") || lower.includes("deadline") || lower.includes("date limite") || lower.includes("tp")) return "deadline";
    if (lower.includes("réunion") || lower.includes("meeting") || lower.includes("rencontre") || lower.includes("équipe")) return "meeting";
    return "personal";
}

function parseGoogleEvent(event: {
    id: string;
    title: string;
    start: string;
    end: string;
    location: string;
    all_day: boolean;
    link: string;
}): CalendarEvent {
    const startDate = event.start.split("T")[0];
    const startTime = event.all_day ? "Journée" : new Date(event.start).toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
    const endTime = event.all_day ? "" : new Date(event.end).toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
    const type = guessEventType(event.title);

    return {
        id: event.id,
        title: event.title,
        date: startDate,
        time: startTime,
        end_time: endTime,
        type,
        priority: type === "exam" ? "high" : type === "deadline" ? "high" : "medium",
        location: event.location,
        all_day: event.all_day,
        link: event.link,
    };
}

export default function CalendarView() {
    const today = new Date();
    const [currentMonth, setCurrentMonth] = useState(today.getMonth());
    const [currentYear, setCurrentYear] = useState(today.getFullYear());
    const [selectedDate, setSelectedDate] = useState<string | null>(null);
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);

    // Vérifier le statut de connexion Google
    const checkConnection = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/google/status`);
            const data = await res.json();
            setIsConnected(data.connected);
            return data.connected;
        } catch {
            setIsConnected(false);
            return false;
        }
    }, []);

    // Récupérer les événements
    const fetchEvents = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/calendar/events?days=30`);
            if (!res.ok) return;
            const data = await res.json();
            const parsed = (data.events || []).map(parseGoogleEvent);
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
    }, [checkConnection, fetchEvents]);

    // Vérifier le paramètre URL (retour de OAuth)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("google_connected") === "true") {
            setIsConnected(true);
            fetchEvents();
            // Nettoyer l'URL
            window.history.replaceState({}, "", window.location.pathname);
        }
    }, [fetchEvents]);

    const handleConnect = async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/google`);
            const data = await res.json();
            if (data.auth_url) {
                window.location.href = data.auth_url;
            }
        } catch {
            console.error("Erreur connexion Google");
        }
    };

    const handleDisconnect = async () => {
        try {
            await fetch(`${API_URL}/api/auth/google`, { method: "DELETE" });
            setIsConnected(false);
            setEvents([]);
        } catch {
            console.error("Erreur déconnexion");
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

    const getEventsForDate = (dateStr: string) => events.filter((e) => e.date === dateStr);

    const isToday = (day: number) =>
        day === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear();

    const upcomingEvents = events
        .filter((e) => {
            const eventDate = new Date(e.date);
            const diff = (eventDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24);
            return diff >= -1 && diff <= 14;
        })
        .sort((a, b) => a.date.localeCompare(b.date));

    const selectedEvents = selectedDate ? getEventsForDate(selectedDate) : [];

    // Si pas connecté, afficher le bouton de connexion
    if (!isConnected && !isLoading) {
        return (
            <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div className="nf-card" style={{ textAlign: "center", padding: "60px 40px" }}>
                    <span style={{ fontSize: "64px", display: "block", marginBottom: "16px" }}>📅</span>
                    <h2 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "8px" }}>
                        Connecte ton Google Calendar
                    </h2>
                    <p style={{ color: "var(--nf-text-secondary)", fontSize: "14px", marginBottom: "24px", maxWidth: "400px", margin: "0 auto 24px" }}>
                        NovaFlow peut lire ton calendrier pour t&apos;afficher tes événements,
                        t&apos;envoyer des rappels et organiser ta journée intelligemment.
                    </p>
                    <button
                        className="nf-btn nf-btn--primary"
                        onClick={handleConnect}
                        style={{ padding: "12px 32px", fontSize: "15px", gap: "8px", display: "inline-flex", alignItems: "center" }}
                    >
                        <span style={{ fontSize: "20px" }}>🔗</span>
                        Connecter Google Calendar
                    </button>
                    <p style={{ color: "var(--nf-text-muted)", fontSize: "12px", marginTop: "16px" }}>
                        🔒 Accès en lecture seule — NovaFlow ne modifie jamais ton calendrier
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="nf-animate-in" style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "20px" }}>
            {/* Calendar Grid */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">📅 {MONTHS_FR[currentMonth]} {currentYear}</span>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        {isConnected && (
                            <span
                                className="nf-card__badge nf-card__badge--success"
                                style={{ cursor: "pointer" }}
                                onClick={handleDisconnect}
                                title="Cliquer pour déconnecter"
                            >
                                ✅ Google connecté
                            </span>
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
                                        ? "1px solid var(--nf-accent-primary)"
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
                                    color: isTodayDay ? "var(--nf-accent-primary)" : "var(--nf-text-primary)",
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
                                        }} />
                                        <div className="nf-task__content">
                                            <div className="nf-task__title">{evt.title}</div>
                                            <div className="nf-task__meta">
                                                {evt.time}{evt.end_time ? ` → ${evt.end_time}` : ""}
                                                {evt.location ? ` · 📍 ${evt.location}` : ""}
                                            </div>
                                        </div>
                                        <div className={`nf-task__priority nf-task__priority--${evt.priority}`} />
                                    </div>
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
                                        <span style={{
                                            padding: "4px 8px",
                                            borderRadius: "6px",
                                            fontSize: "11px",
                                            fontWeight: 700,
                                            background: EVENT_COLORS[evt.type]?.bg || "var(--nf-bg-tertiary)",
                                            color: EVENT_COLORS[evt.type]?.text || "var(--nf-text-muted)",
                                            whiteSpace: "nowrap",
                                        }}>
                                            {relativeDay}
                                        </span>
                                        <div className="nf-task__content">
                                            <div className="nf-task__title">{evt.title}</div>
                                            <div className="nf-task__meta">
                                                {evt.time}
                                                {evt.location ? ` · 📍 ${evt.location}` : ""}
                                            </div>
                                        </div>
                                        <div className={`nf-task__priority nf-task__priority--${evt.priority}`} />
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <p style={{ color: "var(--nf-text-muted)", fontSize: "13px", textAlign: "center", padding: "16px" }}>
                            {isConnected ? "Aucun événement à venir" : "Connecte Google Calendar pour voir tes événements"}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
