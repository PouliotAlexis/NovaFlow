"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const AMBIENT_SOUNDS = [
    { id: "rain", label: "🌧️ Pluie", url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" }, // Placeholders pour démo
    { id: "forest", label: "🌲 Forêt", url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3" },
    { id: "white_noise", label: "🌫️ Bruit blanc", url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3" },
];

export default function FocusMode() {
    const [isActive, setIsActive] = useState(false);
    const [minutes, setMinutes] = useState(25);
    const [seconds, setSeconds] = useState(0);
    const [totalMinutes, setTotalMinutes] = useState(25);
    const [sessionsCompleted, setSessionsCompleted] = useState(0);
    const [currentTask, setCurrentTask] = useState("");
    const [isZenMode, setIsZenMode] = useState(false);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [currentSound, setCurrentSound] = useState<string | null>(null);
    const [stats, setStats] = useState<any>(null);

    const audioRef = useRef<HTMLAudioElement | null>(null);

    // Fetch stats au chargement
    const fetchStats = async () => {
        try {
            const res = await fetch(`${API_URL}/api/focus/stats`);
            if (res.ok) {
                const data = await res.json();
                setStats(data);
                setSessionsCompleted(data.session_count);
            }
        } catch (err) {
            console.error("Erreur stats focus:", err);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    // Timer Logic
    useEffect(() => {
        let interval: ReturnType<typeof setInterval> | null = null;

        if (isActive && (minutes > 0 || seconds > 0)) {
            interval = setInterval(() => {
                if (seconds === 0) {
                    if (minutes === 0) {
                        handleSessionComplete();
                    } else {
                        setMinutes(m => m - 1);
                        setSeconds(59);
                    }
                } else {
                    setSeconds(s => s - 1);
                }
            }, 1000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isActive, minutes, seconds]);

    // Motivation Guard
    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (isActive) {
                e.preventDefault();
                e.returnValue = "Ta session de focus est en cours. Es-tu sûr de vouloir quitter NovaFlow ?";
            }
        };

        window.addEventListener("beforeunload", handleBeforeUnload);
        return () => window.removeEventListener("beforeunload", handleBeforeUnload);
    }, [isActive]);

    const handleSessionComplete = async () => {
        setIsActive(false);
        if (activeSessionId) {
            await fetch(`${API_URL}/api/focus/stop/${activeSessionId}`, { method: "POST" });
            setActiveSessionId(null);
            fetchStats();
        }
        alert("Bravo ! Session de focus terminée. Prends une petite pause.");
    };

    const startTimer = async () => {
        setIsActive(true);
        try {
            const res = await fetch(`${API_URL}/api/focus/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task_title: currentTask || "Focus Libre" })
            });
            if (res.ok) {
                const data = await res.json();
                setActiveSessionId(data.id);
            }
        } catch (err) {
            console.error("Erreur start focus:", err);
        }
    };

    const pauseTimer = () => setIsActive(false);

    const resetTimer = useCallback(() => {
        setIsActive(false);
        setMinutes(totalMinutes);
        setSeconds(0);
    }, [totalMinutes]);

    const toggleZenMode = () => setIsZenMode(!isZenMode);

    const toggleSound = (soundId: string) => {
        if (currentSound === soundId) {
            if (audioRef.current) audioRef.current.pause();
            setCurrentSound(null);
        } else {
            const sound = AMBIENT_SOUNDS.find(s => s.id === soundId);
            if (sound) {
                if (!audioRef.current) audioRef.current = new Audio(sound.url);
                else audioRef.current.src = sound.url;

                audioRef.current.loop = true;
                audioRef.current.play();
                setCurrentSound(soundId);
            }
        }
    };

    const progress = 1 - (minutes * 60 + seconds) / (totalMinutes * 60);
    const circumference = 2 * Math.PI * 120;
    const strokeDashoffset = circumference * (1 - progress);

    const presets = [
        { label: "Pomodoro", min: 25 },
        { label: "Court", min: 15 },
        { label: "Long", min: 50 },
        { label: "Pause", min: 5 },
    ];

    if (isZenMode) {
        return (
            <div style={{
                position: "fixed",
                inset: 0,
                zIndex: 9999,
                background: "var(--nf-bg-primary)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                animation: "nf-fade-in 0.5s ease-out"
            }}>
                <button
                    onClick={toggleZenMode}
                    className="nf-btn nf-btn--ghost"
                    style={{ position: "absolute", top: "24px", right: "24px" }}
                >
                    ✖ Quitter l'Espace Zen
                </button>

                <div style={{ textAlign: "center", maxWidth: "600px", width: "90%" }}>
                    <h1 style={{ fontSize: "24px", marginBottom: "40px", opacity: 0.7 }}>
                        {currentTask || "Session de Focus"}
                    </h1>

                    <div style={{ fontSize: "120px", fontWeight: 700, fontVariantNumeric: "tabular-nums", marginBottom: "40px" }}>
                        {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                    </div>

                    <div style={{ display: "flex", gap: "20px", justifyContent: "center" }}>
                        <button className="nf-btn nf-btn--primary" onClick={isActive ? pauseTimer : startTimer} style={{ padding: "16px 40px", fontSize: "18px" }}>
                            {isActive ? "⏸ Pause" : "▶ Continuer"}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "24px", alignItems: "center" }}>
            {/* Timer Card */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px", textAlign: "center", padding: "40px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h2 style={{
                        fontSize: "20px",
                        fontWeight: 700,
                        background: "var(--nf-accent-gradient)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                    }}>
                        🎯 Espace Zen
                    </h2>
                    <button onClick={toggleZenMode} className="nf-btn nf-btn--ghost" style={{ fontSize: "12px" }}>
                        🖵 Plein écran
                    </button>
                </div>
                <p style={{ color: "var(--nf-text-muted)", fontSize: "13px", marginBottom: "32px" }}>
                    Élimine les distractions. Concentre-toi sur l'essentiel.
                </p>

                {/* Circular Timer */}
                <div style={{ position: "relative", width: "260px", height: "260px", margin: "0 auto 32px" }}>
                    <svg width="260" height="260" style={{ transform: "rotate(-90deg)" }}>
                        <circle cx="130" cy="130" r="120" fill="none" stroke="var(--nf-bg-tertiary)" strokeWidth="6" />
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

                    <div style={{
                        position: "absolute",
                        inset: 0,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                    }}>
                        <span style={{ fontSize: "56px", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                        </span>
                    </div>
                </div>

                {/* Ambient Sounds */}
                <div style={{ display: "flex", gap: "8px", justifyContent: "center", marginBottom: "24px" }}>
                    {AMBIENT_SOUNDS.map(s => (
                        <button
                            key={s.id}
                            className={`nf-btn ${currentSound === s.id ? "nf-btn--primary" : "nf-btn--ghost"}`}
                            onClick={() => toggleSound(s.id)}
                            style={{ fontSize: "12px", padding: "6px 12px" }}
                        >
                            {s.label}
                        </button>
                    ))}
                </div>

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
                        ↩ Reset
                    </button>
                </div>

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
                            {p.min}m
                        </button>
                    ))}
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

            {/* Backend Stats */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px" }}>
                <div className="nf-card__header">
                    <span className="nf-card__title">📊 Statistiques Focus</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div className="nf-stat">
                        <span className="nf-stat__value">{stats?.total_minutes || 0}m</span>
                        <span className="nf-stat__label">Cumul total</span>
                    </div>
                    <div className="nf-stat">
                        <span className="nf-stat__value">{stats?.session_count || 0}</span>
                        <span className="nf-stat__label">Sessions</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
