"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { CheckCircle, Clock, Calendar, Edit2, Trash2, Sparkles, AlertCircle, Book } from "lucide-react";

const API_URL = typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000")
    : "http://127.0.0.1:8000";

interface Task {
    id: string;
    title: string;
    done: boolean;
    priority?: string;
    source_event_start?: string;
    created_at?: string;
    parent_event_id?: string;
    description?: string;
    due_date?: string;
    course_id?: string;
}

interface NovaEvent {
    id: string;
    external_id: string;
    title: string;
    start: string;
    source: string;
}

const EventSelector = ({ currentValue, options, onSelect }: { currentValue: string, options: NovaEvent[], onSelect: (val: string) => void }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [dropdownDirection, setDropdownDirection] = useState<"down" | "up">("down");
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Rendre le menu intelligent (affichage vers le haut si peu d'espace)
    useEffect(() => {
        if (isOpen && dropdownRef.current) {
            const rect = dropdownRef.current.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            const dropdownHeight = 310; // max-height 300px + padding/margin
            if (spaceBelow < dropdownHeight && rect.top > dropdownHeight) {
                setDropdownDirection("up");
            } else {
                setDropdownDirection("down");
            }
        }
    }, [isOpen]);

    const selectedEvent = options.find(o => o.id === currentValue || o.external_id === currentValue);

    const filteredOptions = options.filter(o =>
        o.title.toLowerCase().includes(search.toLowerCase()) ||
        o.source.toLowerCase().includes(search.toLowerCase())
    ).slice(0, 50);

    const getSourceIcon = (source: string) => {
        if (source.includes("google")) return "🌐";
        if (source.includes("outlook")) return "✉️";
        if (source.includes("moodle")) return "🎓";
        if (source.includes("ai")) return "✨";
        return "📅";
    };

    return (
        <div ref={dropdownRef} style={{ position: "relative", width: "100%" }}>
            <div
                className="nf-input"
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    cursor: "pointer",
                    minHeight: "42px",
                    padding: "0 12px"
                }}
            >
                <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {selectedEvent ? (
                        <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px" }}>
                            <span>{getSourceIcon(selectedEvent.source)}</span>
                            {selectedEvent.title}
                        </span>
                    ) : (
                        <span style={{ color: "var(--nf-text-muted)", fontSize: "14px" }}>-- Aucun événement (Standalone) --</span>
                    )}
                </div>
                <span style={{ fontSize: "12px", opacity: 0.7 }}>{isOpen ? "▲" : "▼"}</span>
            </div>

            {isOpen && (
                <div style={{
                    position: "absolute",
                    top: dropdownDirection === "down" ? "100%" : "auto",
                    bottom: dropdownDirection === "up" ? "100%" : "auto",
                    left: 0,
                    right: 0,
                    zIndex: 1000,
                    marginTop: dropdownDirection === "down" ? "5px" : "0",
                    marginBottom: dropdownDirection === "up" ? "5px" : "0",
                    background: "var(--nf-bg-card-solid)",
                    border: "1px solid var(--nf-border)",
                    borderRadius: "var(--nf-radius-sm)",
                    boxShadow: "var(--nf-shadow-lg)",
                    backdropFilter: "blur(20px)",
                    maxHeight: "300px",
                    display: "flex",
                    flexDirection: "column"
                }}>
                    <div style={{ padding: "8px", borderBottom: "1px solid var(--nf-border)" }}>
                        <input
                            type="text"
                            className="nf-input"
                            placeholder="Rechercher un événement..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                        />
                    </div>
                    <div style={{ overflowY: "auto", flex: 1 }}>
                        <div
                            style={{
                                padding: "10px 12px",
                                cursor: "pointer",
                                fontSize: "13px",
                                borderBottom: "1px solid var(--nf-border-dim)",
                                color: currentValue === "" ? "var(--nf-accent)" : "inherit",
                                background: currentValue === "" ? "var(--nf-bg-hover)" : "transparent"
                            }}
                            onClick={() => { onSelect(""); setIsOpen(false); }}
                        >
                            -- Aucun événement (Standalone) --
                        </div>
                        {filteredOptions.map(opt => (
                            <div
                                key={opt.id}
                                style={{
                                    padding: "10px 12px",
                                    cursor: "pointer",
                                    fontSize: "13px",
                                    borderBottom: "1px solid var(--nf-border-dim)",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "2px",
                                    background: (currentValue === opt.id || currentValue === opt.external_id) ? "var(--nf-bg-hover)" : "transparent",
                                    transition: "background 0.2s"
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = "var(--nf-bg-hover)"}
                                onMouseLeave={(e) => e.currentTarget.style.background = (currentValue === opt.id || currentValue === opt.external_id) ? "var(--nf-bg-hover)" : "transparent"}
                                onClick={() => { onSelect(opt.id); setIsOpen(false); }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 500 }}>
                                    <span>{getSourceIcon(opt.source)}</span>
                                    <span style={{ color: (currentValue === opt.id || currentValue === opt.external_id) ? "var(--nf-accent)" : "inherit" }}>
                                        {opt.title}
                                    </span>
                                </div>
                                <div style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginLeft: "24px" }}>
                                    {opt.source} {opt.start ? `• ${new Date(opt.start).toLocaleDateString()}` : ""}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const CourseSelector = ({ currentValue, options, onSelect }: { currentValue: string, options: any[], onSelect: (val: string) => void }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [filter, setFilter] = useState("");
    const wrapperRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const filteredOptions = options.filter(opt => 
        (opt.fullname || opt.name || "").toLowerCase().includes(filter.toLowerCase())
    );

    const selectedCourse = options.find(opt => String(opt.id) === String(currentValue));

    return (
        <div ref={wrapperRef} style={{ position: "relative", width: "100%" }}>
            <div 
                className="nf-input"
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    cursor: "pointer",
                    minHeight: "42px",
                    padding: "0 12px"
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Book size={16} color="var(--nf-accent)" />
                    <span style={{ color: selectedCourse ? "var(--nf-text)" : "var(--nf-text-muted)", fontSize: "14px" }}>
                        {selectedCourse ? (selectedCourse.fullname || selectedCourse.name) : "-- Sélectionner un cours --"}
                    </span>
                </div>
                <span style={{ fontSize: "12px", opacity: 0.7 }}>{isOpen ? "▲" : "▼"}</span>
            </div>

            {isOpen && (
                <div style={{
                    position: "absolute",
                    top: "100%",
                    left: 0,
                    right: 0,
                    zIndex: 1000,
                    marginTop: "5px",
                    background: "var(--nf-bg-card-solid)",
                    border: "1px solid var(--nf-border)",
                    borderRadius: "var(--nf-radius-sm)",
                    boxShadow: "var(--nf-shadow-lg)",
                    backdropFilter: "blur(20px)",
                    maxHeight: "300px",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column"
                }}>
                    <div style={{ padding: "8px", borderBottom: "1px solid var(--nf-border)" }}>
                        <input 
                            autoFocus
                            className="nf-input"
                            placeholder="Filtrer les cours..."
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            onClick={e => e.stopPropagation()}
                            style={{ width: "100%" }}
                        />
                    </div>
                    <div style={{ overflowY: "auto", flex: 1 }}>
                        <div 
                            style={{ 
                                padding: "10px 12px", 
                                cursor: "pointer", 
                                fontSize: "13px",
                                borderBottom: "1px solid var(--nf-border-dim)",
                                color: currentValue === "" ? "var(--nf-accent)" : "var(--nf-text-muted)",
                                background: currentValue === "" ? "var(--nf-bg-hover)" : "transparent"
                            }}
                            onClick={() => { onSelect(""); setIsOpen(false); }}
                        >
                            -- Aucun cours --
                        </div>
                        {filteredOptions.map(opt => (
                            <div
                                key={opt.id}
                                style={{
                                    padding: "10px 12px",
                                    cursor: "pointer",
                                    fontSize: "13px",
                                    borderBottom: "1px solid var(--nf-border-dim)",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "8px",
                                    background: String(currentValue) === String(opt.id) ? "var(--nf-bg-hover)" : "transparent",
                                    transition: "background 0.2s"
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = "var(--nf-bg-hover)"}
                                onMouseLeave={(e) => e.currentTarget.style.background = String(currentValue) === String(opt.id) ? "var(--nf-bg-hover)" : "transparent"}
                                onClick={() => { onSelect(String(opt.id)); setIsOpen(false); }}
                            >
                                <Book size={14} color="var(--nf-accent-dim)" />
                                <span style={{ color: String(currentValue) === String(opt.id) ? "var(--nf-accent)" : "inherit" }}>
                                    {opt.fullname || opt.name}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

interface TaskListProps {
    compact?: boolean;
    onNavigate?: (view: string) => void;
    courseName?: string;
    courseId?: string;
    noWrapper?: boolean;
}

export default function TaskList({ compact = false, onNavigate, courseName, courseId, noWrapper = false }: TaskListProps) {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [localEvents, setLocalEvents] = useState<NovaEvent[]>([]);
    const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
    const [courses, setCourses] = useState<any[]>([]);

    const fetchTasks = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/tasks`, { cache: 'no-store' });
            if (res.ok) {
                const data = await res.json();
                setTasks(data);
            }
        } catch (error) {
            console.warn("Erreur fetch tasks", error);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchEvents = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/calendar/events/simple`, { cache: 'no-store' });
            if (res.ok) {
                const data = await res.json();
                setLocalEvents(data.events || []);
            }
        } catch (error) {
            console.warn("Erreur fetch events", error);
        }
    }, []);

    const fetchCourses = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/v2/moodle/courses`);
            if (res.ok) {
                const data = await res.json();
                setCourses(data || []);
            }
        } catch (error) {
            console.error("Erreur fetch courses", error);
        }
    }, []);

    useEffect(() => {
        fetchTasks();
        fetchEvents();
        fetchCourses();

        // Polling : rafraîchir les tâches toutes les 60s
        const pollInterval = setInterval(() => {
            fetchTasks();
        }, 60_000);

        const onTaskChanged = () => fetchTasks();
        const onAutomationDone = () => fetchTasks();
        window.addEventListener("novaflow-task-changed", onTaskChanged);
        window.addEventListener("novaflow-automation-done", onAutomationDone);
        return () => {
            clearInterval(pollInterval);
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

    const updateTaskCourse = async (taskId: string, courseId: string) => {
        try {
            await fetch(`${API_URL}/api/tasks/${taskId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ course_id: courseId || null })
            });
            await fetchTasks();
            window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
        } catch (error) {
            console.error("Erreur update task course", error);
        }
    };

    const deleteTask = async (taskId: string) => {
        try {
            await fetch(`${API_URL}/api/tasks/${taskId}`, { method: "DELETE" });
            await fetchTasks();
            await fetchEvents();
            window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
        } catch (error) {
            console.error("Erreur delete task", error);
        }
    };

    const updateTaskParentEvent = async (taskId: string, newParentEventId: string) => {
        try {
            const endpoint = `${API_URL}/api/tasks/${taskId}`;
            await fetch(endpoint, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ parent_event_id: newParentEventId || null })
            });
            await fetchTasks();
            await fetchEvents();
            window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
        } catch (error) {
            console.error("Erreur update task parent event", error);
        }
    };

    const forceCreateEvent = async (taskId: string) => {
        try {
            const endpoint = `${API_URL}/api/tasks/${taskId}/force-create-event`;
            const res = await fetch(endpoint, { method: "POST" });
            if (res.ok) {
                await fetchTasks();
                await fetchEvents();
                window.dispatchEvent(new CustomEvent("novaflow-task-changed"));
            } else {
                const err = await res.json();
                alert(`Erreur: ${err.detail}`);
            }
        } catch (error) {
            console.error("Erreur force create event", error);
        }
    };

    const getPriority = (task: Task): string => {
        if (task.priority) return task.priority;
        return "medium";
    };

    const getDueDate = (task: Task): string => {
        const dateString = task.due_date || task.source_event_start;
        if (dateString) {
            const isDateOnly = !dateString.includes("T") || dateString.endsWith("T00:00:00.000Z") || dateString.endsWith("T00:00:00Z");
            // Force 12:00 local time to prevent timezone shifting (UTC midnight becoming 20:00 previous day in EDT)
            const date = isDateOnly ? new Date(dateString.split("T")[0] + "T12:00:00") : new Date(dateString);

            if (isDateOnly) {
                return date.toLocaleDateString("fr-CA", { day: "numeric", month: "short" });
            } else {
                return date.toLocaleDateString("fr-CA", {
                    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"
                }).replace(",", "");
            }
        }
        return "";
    };

    const activeTasks = tasks.filter(t => !t.done);
    
    // Filtrage par cours
    let filteredTasks = tasks;
    if (courseId || courseName) {
        const target = courseName?.toLowerCase() || "";
        const targetCode = target.match(/[a-z]{3,4}-?\d{3,4}/)?.[0];

        filteredTasks = tasks.filter(t => {
            // Priority 1: Direct match via course_id
            if (courseId && t.course_id === courseId) return true;

            // Priority 2: Legacy fallback via parent_event_id
            if (t.parent_event_id) {
                const parentEvent = localEvents.find(e => e.id === t.parent_event_id || e.external_id === t.parent_event_id);
                if (!parentEvent) return false;
                
                // Match direct via course_title du backend (if available)
                if ((parentEvent as any).course_title === courseName) return true;

                const title = parentEvent.title.toLowerCase();
                const cat = ((parentEvent as any).category || "").toLowerCase();

                // Match via code de cours
                if (targetCode && (title.includes(targetCode) || cat.includes(targetCode))) return true;

                // Match via sous-chaîne (catégorie dans le nom du cours)
                if (cat && cat.length > 3 && target.includes(cat)) return true;

                // Fallback via title match
                if (target && title.includes(target)) return true;
                if (target && cat && cat.includes(target)) return true;
            }

            return false;
        });
    }

    const displayTasks = compact ? (courseName ? filteredTasks : activeTasks.slice(0, 5)) : filteredTasks;
    const totalActive = filteredTasks.filter(t => !t.done).length;

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
        const content = (
            <>
                {!noWrapper && (
                    <div className="nf-card__header">
                        <span className="nf-card__title">
                            <CheckCircle size={18} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--nf-success)' }} />
                            {courseName ? "Tâches du cours" : "Upcoming Tasks"}
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span className="nf-card__badge nf-card__badge--info">{totalActive} tasks</span>
                            {onNavigate && (
                                <button className="nf-card__link" onClick={() => onNavigate("tasks")}>
                                    View All
                                </button>
                            )}
                        </div>
                    </div>
                )}
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
                            const parentEvent = task.parent_event_id
                                ? localEvents.find(e => e.id === task.parent_event_id || e.external_id === task.parent_event_id)
                                : null;
                            const eventName = parentEvent ? parentEvent.title : '';
                            const course = task.course_id ? courses.find(c => String(c.id) === String(task.course_id)) : null;
                            const courseNameDisp = course ? (course.fullname || course.name) : '';

                            return (
                                <div
                                    key={task.id}
                                    className={`nf-task nf-task--${priority}`}
                                    onClick={() => toggleTask(task)}
                                    style={{ cursor: "pointer" }}
                                >
                                    <div
                                        className={`nf-task__checkbox ${task.done ? "nf-task__checkbox--checked" : ""}`}
                                        style={{ marginRight: "12px" }}
                                    >
                                        {task.done && <span style={{ fontSize: "10px", color: "white" }}>✓</span>}
                                    </div>
                                    <div className="nf-task__content">
                                        <div className={`nf-task__title ${task.done ? "nf-task__title--done" : ""}`}>
                                            {task.title}
                                        </div>
                                        <div className="nf-task__meta" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
                                            {dueDate && <span style={{ color: "var(--nf-text-muted)", display: "flex", alignItems: "center", gap: "4px" }}><Clock size={12} /> {dueDate}</span>}
                                            {eventName && <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--nf-text-secondary)" }}><Calendar size={12} /> {eventName}</span>}
                                            {courseNameDisp && !courseName && (
                                                <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--nf-accent)", fontSize: "11px", fontWeight: 500 }}>
                                                    <Book size={12} /> {courseNameDisp}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </>
        );

        if (noWrapper) return content;
        return (
            <div className="nf-card nf-card--glow nf-animate-in">
                {content}
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
                            const isEditing = editingTaskId === task.id;
                            const parentEvent = task.parent_event_id
                                ? localEvents.find(e => e.id === task.parent_event_id || e.external_id === task.parent_event_id)
                                : null;
                            const eventName = parentEvent ? parentEvent.title : '';
                            const course = task.course_id ? courses.find(c => String(c.id) === String(task.course_id)) : null;
                            const courseNameDisp = course ? (course.fullname || course.name) : '';

                            return (
                                <div
                                    key={task.id}
                                    className={`nf-task nf-task--${priority}`}
                                    onClick={() => !isEditing && toggleTask(task)}
                                    style={{
                                        cursor: isEditing ? "default" : "pointer",
                                        flexDirection: isEditing ? "column" : "row",
                                        alignItems: isEditing ? "flex-start" : "center",
                                        zIndex: isEditing ? 50 : 1,
                                        position: "relative"
                                    }}
                                >
                                    <div style={{ display: "flex", width: "100%", alignItems: "center" }}>
                                        <div
                                            className={`nf-task__checkbox ${task.done ? "nf-task__checkbox--checked" : ""}`}
                                            onClick={(e) => {
                                                if (isEditing) {
                                                    e.stopPropagation();
                                                    toggleTask(task);
                                                }
                                            }}
                                            style={isEditing ? { cursor: "pointer", marginRight: "12px" } : { marginRight: "12px" }}
                                        >
                                            {task.done && <span style={{ fontSize: "10px", color: "white" }}>✓</span>}
                                        </div>
                                        <div className="nf-task__content">
                                            <div className={`nf-task__title ${task.done ? "nf-task__title--done" : ""}`}>
                                                {task.title}
                                            </div>
                                            <div className="nf-task__meta" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
                                                {dueDate && <span style={{ color: "var(--nf-text-muted)" }}>🕒 {dueDate}</span>}
                                                {eventName && <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--nf-text-secondary)" }}>📅 {eventName}</span>}
                                                {courseNameDisp && !courseName && (
                                                    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--nf-accent)", fontSize: "11px", fontWeight: 600 }}>
                                                        <Book size={12} /> {courseNameDisp}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="nf-task__actions">
                                            <button
                                                className="nf-btn--icon"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setEditingTaskId(isEditing ? null : task.id);
                                                }}
                                                title={isEditing ? "Close edit" : "Edit task"}
                                            >
                                                {isEditing ? "❌" : "✏️"}
                                            </button>
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

                                    {isEditing && (
                                        <div style={{ padding: "10px", marginTop: "10px", width: "100%", borderTop: "1px solid rgba(255,255,255,0.1)", display: "flex", flexDirection: "column", gap: "10px" }} onClick={e => e.stopPropagation()}>
                                            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                                                <label style={{ fontSize: "12px", color: "var(--nf-text-secondary)" }}>Event associé :</label>
                                                <EventSelector
                                                    currentValue={task.parent_event_id || ""}
                                                    options={localEvents}
                                                    onSelect={(val) => updateTaskParentEvent(task.id, val)}
                                                />
                                            </div>

                                            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                                                <label style={{ fontSize: "12px", color: "var(--nf-text-secondary)" }}>Cours associé :</label>
                                                <CourseSelector
                                                    currentValue={task.course_id || ""}
                                                    options={courses}
                                                    onSelect={(val) => updateTaskCourse(task.id, val)}
                                                />
                                            </div>

                                            {!task.parent_event_id && (
                                                <div>
                                                    <button
                                                        className="nf-btn nf-btn--secondary"
                                                        onClick={() => forceCreateEvent(task.id)}
                                                        style={{ fontSize: "12px", padding: "4px 8px" }}
                                                    >
                                                        ✨ Créer un événement lié (AI)
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}
