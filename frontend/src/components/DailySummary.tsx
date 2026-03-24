"use client";

import React, { useState, useEffect, useCallback } from "react";
import { BarChart3 } from "lucide-react";

export default function DailySummary() {
    const [stats, setStats] = useState({ total: 0, completed: 0, tasks: 0, ticks: 0 });

    const fetchStats = useCallback(async () => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
            const res = await fetch(`${API_URL}/api/tasks`);
            if (res.ok) {
                const tasks = await res.json();
                const total = tasks.length;
                const completed = tasks.filter((t: any) => t.done).length;
                const active = tasks.filter((t: any) => !t.done).length;
                setStats({ total, completed, tasks: active, ticks: completed });
            }
        } catch (e) {
            console.error("DailySummary fetch error", e);
        }
    }, []);

    useEffect(() => {
        fetchStats();
        const onTaskChanged = () => fetchStats();
        window.addEventListener("novaflow-task-changed", onTaskChanged);
        return () => window.removeEventListener("novaflow-task-changed", onTaskChanged);
    }, [fetchStats]);

    const pct = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;
    const radius = 36;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (pct / 100) * circumference;

    return (
        <div className="nf-card nf-card--glow nf-animate-in">
            <div className="nf-card__header">
                <span className="nf-card__title">
                    <BarChart3 size={18} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--nf-accent)' }} />
                    Daily Summary
                </span>
            </div>
            <div className="nf-daily-summary">
                <div className="nf-daily-summary__circle">
                    <svg width="90" height="90" viewBox="0 0 90 90">
                        {/* Background circle */}
                        <circle cx="45" cy="45" r={radius} fill="none" stroke="rgba(124,92,252,0.15)" strokeWidth="6" />
                        {/* Progress circle */}
                        <circle
                            cx="45" cy="45" r={radius} fill="none"
                            stroke="url(#progressGrad)" strokeWidth="6"
                            strokeLinecap="round"
                            strokeDasharray={circumference}
                            strokeDashoffset={strokeDashoffset}
                            style={{ transition: "stroke-dashoffset 0.8s ease" }}
                        />
                        <defs>
                            <linearGradient id="progressGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stopColor="#6366f1" />
                                <stop offset="100%" stopColor="#a855f7" />
                            </linearGradient>
                        </defs>
                    </svg>
                    <div className="nf-daily-summary__percent">{pct}%</div>
                </div>
                <div className="nf-daily-summary__info">
                    <h3>Daily Goals Achieved</h3>
                    <div className="nf-daily-summary__stat">
                        <span className="nf-daily-summary__stat-dot" style={{ background: "var(--nf-accent)" }} />
                        Tasks Completed
                    </div>
                    <div className="nf-daily-summary__stat">
                        <span className="nf-daily-summary__stat-dot" style={{ background: "var(--nf-info)" }} />
                        {stats.tasks} Tasks Remaining
                    </div>
                    <div className="nf-daily-summary__stat">
                        <span className="nf-daily-summary__stat-dot" style={{ background: "var(--nf-success)" }} />
                        {stats.ticks} Completed
                    </div>
                </div>
            </div>
        </div>
    );
}
