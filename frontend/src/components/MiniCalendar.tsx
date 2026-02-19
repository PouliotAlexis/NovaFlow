"use client";

import React, { useState, useEffect, useCallback } from "react";

interface CalendarEvent {
    title?: string;
    summary?: string;
    start?: string;
    end?: string;
    all_day?: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function MiniCalendar() {
    const now = new Date();
    const [selectedDay, setSelectedDay] = useState(now.getDate());
    const [allEvents, setAllEvents] = useState<CalendarEvent[]>([]);

    const year = now.getFullYear();
    const month = now.getMonth();
    const today = now.getDate();

    const monthName = now.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDayOfWeek = new Date(year, month, 1).getDay();
    const dayHeaders = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

    // Fetch all events for the month (remaining days)
    const fetchMonthEvents = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/calendar/events?days=${daysInMonth}`);
            if (res.ok) {
                const data = await res.json();
                setAllEvents(data.events || []);
            }
        } catch (e) {
            console.error("MiniCalendar fetch error", e);
        }
    }, [daysInMonth]);

    useEffect(() => {
        fetchMonthEvents();
        const onUpdate = () => fetchMonthEvents();
        window.addEventListener("novaflow-automation-done", onUpdate);
        window.addEventListener("novaflow-account-changed", onUpdate);
        return () => {
            window.removeEventListener("novaflow-automation-done", onUpdate);
            window.removeEventListener("novaflow-account-changed", onUpdate);
        };
    }, [fetchMonthEvents]);

    // Filter events for the selected day
    const eventsForDay = allEvents.filter((evt) => {
        if (!evt.start) return false;
        const startStr = evt.start;
        // Handle both datetime (2026-02-19T10:00:00) and date-only (2026-02-19)
        const evtYear = parseInt(startStr.slice(0, 4));
        const evtMonth = parseInt(startStr.slice(5, 7)) - 1; // 0-indexed
        const evtDay = parseInt(startStr.slice(8, 10));
        return evtYear === year && evtMonth === month && evtDay === selectedDay;
    });

    // Days that have events (for dot indicators)
    const daysWithEvents = new Set(
        allEvents
            .filter((evt) => evt.start)
            .map((evt) => {
                const s = evt.start!;
                const eY = parseInt(s.slice(0, 4));
                const eM = parseInt(s.slice(5, 7)) - 1;
                const eD = parseInt(s.slice(8, 10));
                return eY === year && eM === month ? eD : -1;
            })
            .filter((d) => d > 0)
    );

    const handleDayClick = (day: number) => {
        setSelectedDay(day);
    };

    const eventColors = ["#7c5cfc", "#ef4444", "#3b82f6", "#22c55e", "#f59e0b"];

    const isSelectedToday = selectedDay === today;
    const selectedDateObj = new Date(year, month, selectedDay);
    const eventsLabel = isSelectedToday
        ? "Today's Events"
        : selectedDateObj.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

    return (
        <div className="nf-card nf-card--glow nf-animate-in">
            <div className="nf-card__header">
                <span className="nf-card__title">📅 Mini Calendar</span>
            </div>

            <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "8px", color: "var(--nf-text)" }}>
                {monthName}
            </div>

            <div className="nf-mini-cal__grid">
                {dayHeaders.map((d) => (
                    <div key={d} className="nf-mini-cal__header">{d}</div>
                ))}
                {Array.from({ length: firstDayOfWeek }).map((_, i) => (
                    <div key={`empty-${i}`} className="nf-mini-cal__day nf-mini-cal__day--empty" />
                ))}
                {Array.from({ length: daysInMonth }).map((_, i) => {
                    const day = i + 1;
                    const isToday = day === today;
                    const isSelected = day === selectedDay && !isToday;
                    const hasEvent = daysWithEvents.has(day);
                    return (
                        <div
                            key={day}
                            className={`nf-mini-cal__day ${isToday ? "nf-mini-cal__day--today" : ""} ${isSelected ? "nf-mini-cal__day--selected" : ""}`}
                            onClick={() => handleDayClick(day)}
                            style={{ cursor: "pointer", position: "relative" }}
                        >
                            {day}
                            {hasEvent && !isToday && (
                                <span style={{
                                    position: "absolute",
                                    bottom: "1px",
                                    left: "50%",
                                    transform: "translateX(-50%)",
                                    width: "4px",
                                    height: "4px",
                                    borderRadius: "50%",
                                    background: "var(--nf-accent)",
                                }} />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Events for selected day */}
            <div className="nf-mini-cal__events">
                <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--nf-text)", marginBottom: "8px" }}>
                    {eventsLabel}
                </div>
                {eventsForDay.length === 0 ? (
                    <div style={{ fontSize: "11px", color: "var(--nf-text-muted)" }}>No events</div>
                ) : (
                    eventsForDay.slice(0, 5).map((evt, i) => {
                        const name = evt.title || evt.summary || "Untitled";
                        let timeLabel = "All day";
                        if (!evt.all_day && evt.start && evt.start.includes("T")) {
                            timeLabel = new Date(evt.start).toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
                        }
                        return (
                            <div key={i} className="nf-mini-cal__event">
                                <span className="nf-mini-cal__event-dot" style={{ background: eventColors[i % eventColors.length] }} />
                                <span style={{ color: "var(--nf-text-secondary)", fontSize: "11px" }}>
                                    <span style={{ color: "var(--nf-text-muted)", marginRight: "4px" }}>{timeLabel} ·</span>
                                    {name}
                                </span>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
