"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_URL = typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    : "http://localhost:8000";

interface Task {
    id: string;
    title: string;
    done: boolean;
    priority?: string;
    source_event_start?: string;
    created_at?: string;
}

interface TaskListProps {
    compact?: boolean;
    onNavigate?: (view: string) => void;
}

export default function TaskList({ compact = false, onNavigate }: TaskListProps) {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTasks = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/tasks`);
            if (res.ok) {
                const data = await res.json();
                setTasks(data);
            }
        } catch (error) {
            console.error("Erreur fetch tasks", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTasks();
        const onTaskChanged = () => fetchTasks();
        const onAutomationDone = () => fetchTasks();
        window.addEventListener("novaflow-task-changed", onTaskChanged);
        window.addEventListener("novaflow-automation-done", onAutomationDone);
        return () => {
            window.removeEventListener("novaflow-task-changed", onTaskChanged);
            window.removeEventListener("novaflow-automation-done", onAutomationDone);
        };
    }, [fetchTasks]);

    const toggleTask = async (task: Task) => {
        try {
            await fetch(`${API_URL}/api/tasks/${task.id}/toggle`, { method: "PATCH" });
            await fetchTasks();
            window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
        } catch (error) {
            console.error("Erreur toggle task", error);
        }
    };

    const deleteTask = async (taskId: string) => {
        try {
            await fetch(`${API_URL}/api/tasks/${taskId}`, { method: "DELETE" });
            await fetchTasks();
            window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
        } catch (error) {
            console.error("Erreur delete task", error);
        }
    };

    const getPriority = (task: Task): string => {
        if (task.priority) return task.priority;
        return "medium";
    };

    const getDueDate = (task: Task): string => {
        if (task.source_event_start) {
            const date = new Date(task.source_event_start);
            const now = new Date();
            const diff = date.getTime() - now.getTime();
            const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
            if (days === 0) return "Due Today";
            if (days === 1) return "Due Tomorrow";
            if (days < 0) return "Overdue";
            return `Due in ${days} days`;
        }
        return "";
    };

    const activeTasks = tasks.filter(t => !t.done);
    const displayTasks = compact ? activeTasks.slice(0, 5) : tasks;
    const totalActive = activeTasks.length;

    if (loading) {
        return (
            <div className="nf-card nf-animate-in">
                <div className="nf-loading">
                    <span className="nf-spinner">⏳</span> Loading tasks...
                </div>
            </div>
        );
    }

    // Dashboard compact mode
    if (compact) {
        return (
            <div className="nf-card nf-card--glow nf-animate-in">
                <div className="nf-card__header">
                    <span className="nf-card__title">✅ Upcoming Tasks</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span className="nf-card__badge nf-card__badge--info">{totalActive} tasks</span>
                        {onNavigate && (
                            <button className="nf-card__link" onClick={() => onNavigate("tasks")}>
                                View All
                            </button>
                        )}
                    </div>
                </div>
                <div className="nf-task-list">
                    {displayTasks.length === 0 ? (
                        <div className="nf-empty-state">
                            <span className="nf-empty-state__icon">🎉</span>
                            <span className="nf-empty-state__text">All done!</span>
                        </div>
                    ) : (
                        displayTasks.map((task) => {
                            const priority = getPriority(task);
                            const dueDate = getDueDate(task);
                            return (
                                <div
                                    key={task.id}
                                    className={`nf-task nf-task--${priority}`}
                                    onClick={() => toggleTask(task)}
                                    style={{ cursor: "pointer" }}
                                >
                                    <div
                                        className={`nf-task__checkbox ${task.done ? "nf-task__checkbox--checked" : ""}`}
                                    >
                                        {task.done && <span style={{ fontSize: "10px", color: "white" }}>✓</span>}
                                    </div>
                                    <div className="nf-task__content">
                                        <div className={`nf-task__title ${task.done ? "nf-task__title--done" : ""}`}>
                                            {task.title}
                                        </div>
                                        <div className="nf-task__meta">
                                            <span className={`nf-task__priority-badge nf-task__priority-badge--${priority}`}>
                                                {priority.charAt(0).toUpperCase() + priority.slice(1)}
                                            </span>
                                            {dueDate && <span>{dueDate}</span>}
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        );
    }

    // Full page mode
    return (
        <div className="nf-animate-in">
            <div className="nf-page-header">
                <h1 className="nf-page-header__title">Tasks</h1>
                <p className="nf-page-header__subtitle">Manage your priorities</p>
            </div>
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">All Tasks</span>
                    <span className="nf-card__badge nf-card__badge--info">{totalActive} active</span>
                </div>
                <div className="nf-task-list">
                    {tasks.length === 0 ? (
                        <div className="nf-empty-state">
                            <span className="nf-empty-state__icon">📋</span>
                            <span className="nf-empty-state__text">No tasks yet</span>
                        </div>
                    ) : (
                        tasks.map((task) => {
                            const priority = getPriority(task);
                            const dueDate = getDueDate(task);
                            return (
                                <div
                                    key={task.id}
                                    className={`nf-task nf-task--${priority}`}
                                    onClick={() => toggleTask(task)}
                                    style={{ cursor: "pointer" }}
                                >
                                    <div
                                        className={`nf-task__checkbox ${task.done ? "nf-task__checkbox--checked" : ""}`}
                                    >
                                        {task.done && <span style={{ fontSize: "10px", color: "white" }}>✓</span>}
                                    </div>
                                    <div className="nf-task__content">
                                        <div className={`nf-task__title ${task.done ? "nf-task__title--done" : ""}`}>
                                            {task.title}
                                        </div>
                                        <div className="nf-task__meta">
                                            <span className={`nf-task__priority-badge nf-task__priority-badge--${priority}`}>
                                                {priority.charAt(0).toUpperCase() + priority.slice(1)}
                                            </span>
                                            {dueDate && <span>{dueDate}</span>}
                                        </div>
                                    </div>
                                    <div className="nf-task__actions">
                                        <button
                                            className="nf-btn--icon"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                deleteTask(task.id);
                                            }}
                                            title="Delete task"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}
