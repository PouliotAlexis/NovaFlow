"use client";

import React, { useState, useEffect } from "react";

export default function SmartFeed() {
    const [greeting, setGreeting] = useState("");
    const [dateStr, setDateStr] = useState("");
    const [stats, setStats] = useState({
        tasks: 0,
        events: 0,
        completed: 0,
        docs: 0
    });

    // Calcul salutation et date
    useEffect(() => {
        const now = new Date();
        setGreeting(
            now.getHours() < 12
                ? "Bon matin"
                : now.getHours() < 18
                    ? "Bon après-midi"
                    : "Bonsoir"
        );
        setDateStr(
            now.toLocaleDateString("fr-CA", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            })
        );
    }, []);

    // Polling des données pour mettre à jour les stats et déclencher l'analyse
    useEffect(() => {
        const fetchData = async () => {
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

                // 1. Tâches
                try {
                    const tasksRes = await fetch(`${API_URL}/api/tasks`);
                    if (tasksRes.ok) {
                        const tasks = await tasksRes.json();
                        const activeTasks = tasks.filter((t: any) => !t.done).length;
                        const doneTasks = tasks.filter((t: any) => t.done).length;

                        setStats(prev => ({
                            ...prev,
                            tasks: activeTasks,
                            completed: doneTasks
                        }));
                    }
                } catch (e) {
                    console.error("Erreur fetch tasks", e);
                }

                // 2. Calendrier (Déclenche l'analyse IA en background !)
                try {
                    const eventsRes = await fetch(`${API_URL}/api/calendar/events?days=3`);
                    if (eventsRes.ok) {
                        const eventsData = await eventsRes.json();
                        const eventsCount = eventsData.count || 0;

                        setStats(prev => ({
                            ...prev,
                            events: eventsCount
                        }));
                    } else {
                        console.warn("Erreur fetch calendar", eventsRes.status);
                    }
                } catch (e) {
                    console.error("Erreur fetch calendar", e);
                }

                // 3. Documents (optionnel)
                // ...

            } catch (error) {
                console.error("Erreur chargement SmartFeed", error);
            }
        };

        fetchData();
        // Rafraîchir toutes les 30 secondes pour garder le dashboard à jour
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="nf-card nf-smart-feed nf-animate-in">
            <div className="nf-smart-feed__greeting">
                {greeting || "Bonjour"}, Alexis 👋
            </div>
            <p className="nf-smart-feed__summary">
                {dateStr
                    ? `Aujourd'hui c'est ${dateStr}. `
                    : "Chargement... "}
                {stats.tasks > 0
                    ? `Tu as ${stats.tasks} tâches à accomplir et ${stats.events} événements à venir.`
                    : "Rien de prévu pour l'instant. Profites-en !"}
            </p>

            <div className="nf-smart-feed__stats">
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-accent-primary)" }}>{stats.tasks}</span>
                    <span className="nf-stat__label">Tâches</span>
                </div>
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-warning)" }}>{stats.events}</span>
                    <span className="nf-stat__label">Échéances</span>
                </div>
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-success)" }}>{stats.completed}</span>
                    <span className="nf-stat__label">Complétées</span>
                </div>
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-info)" }}>{stats.docs}</span>
                    <span className="nf-stat__label">Documents</span>
                </div>
            </div>
        </div>
    );
}
