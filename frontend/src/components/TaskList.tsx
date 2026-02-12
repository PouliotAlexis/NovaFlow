"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Task {
    id: string;
    title: string;
    meta: string;
    priority: "high" | "medium" | "low";
    done: boolean;
}

export default function TaskList() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchTasks = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/tasks`);
            if (res.ok) {
                const data = await res.json();
                setTasks(data);
            }
        } catch (error) {
            console.error("Erreur chargement tâches:", error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Charger initialement et poller toutes les 5 secondes pour voir les tâches créées par l'IA
    useEffect(() => {
        fetchTasks();
        const interval = setInterval(fetchTasks, 5000);
        return () => clearInterval(interval);
    }, [fetchTasks]);

    const toggleTask = async (id: string) => {
        // Optimistic update
        setTasks((prev) =>
            prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t))
        );

        try {
            await fetch(`${API_URL}/api/tasks/${id}/toggle`, {
                method: "PATCH",
            });
        } catch (error) {
            console.error("Erreur toggle tâche:", error);
            fetchTasks(); // Rollback en cas d'erreur
        }
    };

    const deleteTask = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        if (!confirm("Supprimer cette tâche ?")) return;

        try {
            await fetch(`${API_URL}/api/tasks/${id}`, {
                method: "DELETE",
            });
            fetchTasks();
        } catch (error) {
            console.error("Erreur suppression tâche:", error);
        }
    }

    if (isLoading && tasks.length === 0) {
        return (
            <div className="nf-card nf-animate-in">
                <div className="nf-card__header">
                    <span className="nf-card__title">✅ Tâches</span>
                </div>
                <div style={{ padding: "20px", textAlign: "center", color: "var(--nf-text-muted)" }}>
                    Chargement...
                </div>
            </div>
        );
    }

    return (
        <div className="nf-card nf-animate-in">
            <div className="nf-card__header">
                <span className="nf-card__title">✅ Tâches</span>
                <span className="nf-card__badge nf-card__badge--info">
                    {tasks.filter((t) => !t.done).length} actives
                </span>
            </div>

            <div className="nf-task-list">
                {tasks.length === 0 ? (
                    <div style={{ padding: "20px", textAlign: "center", color: "var(--nf-text-muted)", fontSize: "14px" }}>
                        Aucune tâche. Demande à l'IA d'en créer !<br />
                        <em style={{ fontSize: "12px", opacity: 0.7 }}>Ex: "Rappelle-moi d'acheter du pain"</em>
                    </div>
                ) : (
                    tasks.map((task) => (
                        <div
                            key={task.id}
                            className="nf-task"
                            onClick={() => toggleTask(task.id)}
                            style={{ position: "relative", group: "task" } as any}
                        >
                            <div
                                className={`nf-task__checkbox ${task.done ? "nf-task__checkbox--checked" : ""
                                    }`}
                            >
                                {task.done && "✓"}
                            </div>
                            <div className="nf-task__content">
                                <div
                                    className={`nf-task__title ${task.done ? "nf-task__title--done" : ""
                                        }`}
                                >
                                    {task.title}
                                </div>
                                <div className="nf-task__meta">{task.meta}</div>
                            </div>
                            <div className={`nf-task__priority nf-task__priority--${task.priority}`} />

                            {/* Bouton supprimer (visible au survol, géré via CSS ou simple click droit en prod, ici simple bouton pour demo) */}
                            <button
                                style={{
                                    background: "none",
                                    border: "none",
                                    color: "var(--nf-text-muted)",
                                    cursor: "pointer",
                                    marginLeft: "8px",
                                    fontSize: "16px"
                                }}
                                onClick={(e) => deleteTask(e, task.id)}
                                title="Supprimer"
                            >
                                ×
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
