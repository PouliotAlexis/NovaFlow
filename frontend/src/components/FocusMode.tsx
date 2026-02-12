"use client";

import React, { useState, useEffect, useCallback } from "react";

export default function FocusMode() {
    const [isActive, setIsActive] = useState(false);
    const [minutes, setMinutes] = useState(25);
    const [seconds, setSeconds] = useState(0);
    const [totalMinutes, setTotalMinutes] = useState(25);
    const [sessionsCompleted, setSessionsCompleted] = useState(0);
    const [currentTask, setCurrentTask] = useState("Étudier pour l'examen intra");

    useEffect(() => {
        let interval: ReturnType<typeof setInterval> | null = null;

        if (isActive && (minutes > 0 || seconds > 0)) {
            interval = setInterval(() => {
                if (seconds === 0) {
                    if (minutes === 0) {
                        setIsActive(false);
                        setSessionsCompleted((s) => s + 1);
                    } else {
                        setMinutes(minutes - 1);
                        setSeconds(59);
                    }
                } else {
                    setSeconds(seconds - 1);
                }
            }, 1000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isActive, minutes, seconds]);

    const startTimer = useCallback(() => setIsActive(true), []);
    const pauseTimer = useCallback(() => setIsActive(false), []);
    const resetTimer = useCallback(() => {
        setIsActive(false);
        setMinutes(totalMinutes);
        setSeconds(0);
    }, [totalMinutes]);

    const progress = 1 - (minutes * 60 + seconds) / (totalMinutes * 60);
    const circumference = 2 * Math.PI * 120;
    const strokeDashoffset = circumference * (1 - progress);

    const presets = [
        { label: "Pomodoro", min: 25 },
        { label: "Court", min: 15 },
        { label: "Long", min: 50 },
        { label: "Pause", min: 5 },
    ];

    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "24px", alignItems: "center" }}>
            {/* Timer Card */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px", textAlign: "center", padding: "40px" }}>
                <h2 style={{
                    fontSize: "20px",
                    fontWeight: 700,
                    marginBottom: "8px",
                    background: "var(--nf-accent-gradient)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                }}>
                    🎯 Focus Mode
                </h2>
                <p style={{ color: "var(--nf-text-muted)", fontSize: "13px", marginBottom: "32px" }}>
                    Élimine les distractions. Concentre-toi.
                </p>

                {/* Circular Timer */}
                <div style={{ position: "relative", width: "260px", height: "260px", margin: "0 auto 32px" }}>
                    <svg width="260" height="260" style={{ transform: "rotate(-90deg)" }}>
                        {/* Background circle */}
                        <circle
                            cx="130" cy="130" r="120"
                            fill="none"
                            stroke="var(--nf-bg-tertiary)"
                            strokeWidth="6"
                        />
                        {/* Progress circle */}
                        <circle
                            cx="130" cy="130" r="120"
                            fill="none"
                            stroke="url(#focusGradient)"
                            strokeWidth="6"
                            strokeLinecap="round"
                            strokeDasharray={circumference}
                            strokeDashoffset={strokeDashoffset}
                            style={{ transition: "stroke-dashoffset 1s linear" }}
                        />
                        <defs>
                            <linearGradient id="focusGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stopColor="#6366f1" />
                                <stop offset="100%" stopColor="#a855f7" />
                            </linearGradient>
                        </defs>
                    </svg>

                    {/* Timer Display */}
                    <div style={{
                        position: "absolute",
                        inset: 0,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                    }}>
                        <span style={{
                            fontSize: "56px",
                            fontWeight: 700,
                            fontVariantNumeric: "tabular-nums",
                            letterSpacing: "-0.02em",
                        }}>
                            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                        </span>
                        <span style={{ color: "var(--nf-text-muted)", fontSize: "13px" }}>
                            {isActive ? "En cours..." : progress > 0 ? "En pause" : "Prêt"}
                        </span>
                    </div>
                </div>

                {/* Controls */}
                <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginBottom: "24px" }}>
                    {!isActive ? (
                        <button className="nf-btn nf-btn--primary" onClick={startTimer} style={{ minWidth: "120px" }}>
                            ▶ {progress > 0 ? "Reprendre" : "Commencer"}
                        </button>
                    ) : (
                        <button className="nf-btn nf-btn--ghost" onClick={pauseTimer} style={{ minWidth: "120px" }}>
                            ⏸ Pause
                        </button>
                    )}
                    <button className="nf-btn nf-btn--ghost" onClick={resetTimer}>
                        ↩ Réinitialiser
                    </button>
                </div>

                {/* Presets */}
                <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
                    {presets.map((p) => (
                        <button
                            key={p.label}
                            className={`nf-btn ${totalMinutes === p.min ? "nf-btn--primary" : "nf-btn--ghost"}`}
                            onClick={() => {
                                setTotalMinutes(p.min);
                                setMinutes(p.min);
                                setSeconds(0);
                                setIsActive(false);
                            }}
                            style={{ fontSize: "12px", padding: "6px 14px" }}
                        >
                            {p.label} ({p.min}m)
                        </button>
                    ))}
                </div>
            </div>

            {/* Stats & Task */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", width: "100%", maxWidth: "500px" }}>
                <div className="nf-card" style={{ textAlign: "center" }}>
                    <div className="nf-stat">
                        <span className="nf-stat__value" style={{ color: "var(--nf-accent-primary)" }}>
                            {sessionsCompleted}
                        </span>
                        <span className="nf-stat__label">Sessions aujourd&apos;hui</span>
                    </div>
                </div>

                <div className="nf-card" style={{ textAlign: "center" }}>
                    <div className="nf-stat">
                        <span className="nf-stat__value" style={{ color: "var(--nf-success)" }}>
                            {sessionsCompleted * totalMinutes}m
                        </span>
                        <span className="nf-stat__label">Temps concentré</span>
                    </div>
                </div>
            </div>

            {/* Current Focus Task */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px" }}>
                <div className="nf-card__header">
                    <span className="nf-card__title">📝 Objectif de la session</span>
                </div>
                <input
                    className="nf-chat__input"
                    value={currentTask}
                    onChange={(e) => setCurrentTask(e.target.value)}
                    placeholder="Sur quoi travailles-tu ?"
                    style={{ width: "100%" }}
                />
            </div>
        </div>
    );
}
