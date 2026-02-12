"use client";

import React, { useState } from "react";

interface Task {
    id: string;
    title: string;
    meta: string;
    priority: "high" | "medium" | "low";
    done: boolean;
}

const SAMPLE_TASKS: Task[] = [
    {
        id: "1",
        title: "Configurer la connexion Google Calendar",
        meta: "NovaFlow · Setup",
        priority: "high",
        done: false,
    },
    {
        id: "2",
        title: "Glisser un premier PDF dans la Drop Zone",
        meta: "NovaFlow · Démarrage",
        priority: "medium",
        done: false,
    },
    {
        id: "3",
        title: "Tester le chat avec l'IA locale",
        meta: "NovaFlow · Test",
        priority: "low",
        done: false,
    },
];

export default function TaskList() {
    const [tasks, setTasks] = useState<Task[]>(SAMPLE_TASKS);

    const toggleTask = (id: string) => {
        setTasks((prev) =>
            prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t))
        );
    };

    return (
        <div className="nf-card nf-animate-in">
            <div className="nf-card__header">
                <span className="nf-card__title">✅ Tâches</span>
                <span className="nf-card__badge nf-card__badge--info">
                    {tasks.filter((t) => !t.done).length} actives
                </span>
            </div>

            <div className="nf-task-list">
                {tasks.map((task) => (
                    <div
                        key={task.id}
                        className="nf-task"
                        onClick={() => toggleTask(task.id)}
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
                    </div>
                ))}
            </div>
        </div>
    );
}
