"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const AMBIENT_SOUNDS = [
    { id: "rain", label: "🌧️ Rain", url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" },
    { id: "forest", label: "🌲 Forest", url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3" },
    { id: "white_noise", label: "🌫️ White Noise", url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3" },
];

interface FocusModeProps {
    compact?: boolean;
}

export default function FocusMode({ compact = false }: FocusModeProps) {
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

    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (isActive) {
                e.preventDefault();
                e.returnValue = "Your focus session is in progress. Are you sure you want to leave?";
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
        alert("Session complete! Take a short break.");
    };

    const startTimer = async () => {
        setIsActive(true);
        try {
            const res = await fetch(`${API_URL}/api/focus/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task_title: currentTask || "Focus Session" })
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
        { label: "Short", min: 15 },
        { label: "Long", min: 50 },
        { label: "Break", min: 5 },
    ];

    // Dashboard compact mode
    if (compact) {
        const compactCirc = 2 * Math.PI * 36;
        const compactOffset = compactCirc * (1 - progress);

        return (
            <div className="nf-card nf-card--glow nf-animate-in">
                <div className="nf-card__header">
                    <span className="nf-card__title">🎯 Focus Mode</span>
                    {isActive && <span className="nf-card__badge nf-card__badge--success">Active</span>}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                    {/* Mini timer circle */}
                    <div style={{ position: "relative", width: "80px", height: "80px", flexShrink: 0 }}>
                        <svg width="80" height="80" style={{ transform: "rotate(-90deg)" }}>
                            <circle cx="40" cy="40" r="36" fill="none" stroke="rgba(124,92,252,0.15)" strokeWidth="4" />
                            <circle cx="40" cy="40" r="36" fill="none" stroke="url(#focusCompactGrad)" strokeWidth="4"
                                strokeLinecap="round"
                                strokeDasharray={compactCirc}
                                strokeDashoffset={compactOffset}
                                style={{ transition: "stroke-dashoffset 1s linear" }}
                            />
                            <defs>
                                <linearGradient id="focusCompactGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stopColor="#6366f1" />
                                    <stop offset="100%" stopColor="#a855f7" />
                                </linearGradient>
                            </defs>
                        </svg>
                        <div style={{
                            position: "absolute", inset: 0,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "14px", fontWeight: 700, fontVariantNumeric: "tabular-nums",
                            color: "var(--nf-text)"
                        }}>
                            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                        </div>
                    </div>

                    <div style={{ flex: 1 }}>
                        <div style={{ fontSize: "12px", color: "var(--nf-text-secondary)", marginBottom: "8px" }}>
                            {isActive ? "Focusing..." : "Ready to focus"}
                        </div>
                        <div style={{ display: "flex", gap: "6px" }}>
                            {!isActive ? (
                                <button className="nf-btn nf-btn--primary" onClick={startTimer} style={{ fontSize: "11px", padding: "6px 12px" }}>
                                    ▶ Start
                                </button>
                            ) : (
                                <button className="nf-btn nf-btn--ghost" onClick={pauseTimer} style={{ fontSize: "11px", padding: "6px 12px" }}>
                                    ⏸ Pause
                                </button>
                            )}
                            <button className="nf-btn nf-btn--ghost" onClick={resetTimer} style={{ fontSize: "11px", padding: "6px 12px" }}>
                                ↩ Reset
                            </button>
                        </div>
                        <div style={{ display: "flex", gap: "4px", marginTop: "8px" }}>
                            {presets.map((p) => (
                                <button
                                    key={p.label}
                                    className={`nf-btn ${totalMinutes === p.min ? "nf-btn--primary" : "nf-btn--ghost"}`}
                                    onClick={() => { setTotalMinutes(p.min); setMinutes(p.min); setSeconds(0); setIsActive(false); }}
                                    style={{ fontSize: "10px", padding: "3px 8px" }}
                                >
                                    {p.min}m
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Zen Mode (fullscreen)
    if (isZenMode) {
        return (
            <div style={{
                position: "fixed", inset: 0, zIndex: 9999,
                background: "var(--nf-bg-primary)",
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
            }} className="nf-fade-in">
                <button onClick={toggleZenMode} className="nf-btn nf-btn--ghost"
                    style={{ position: "absolute", top: "24px", right: "24px" }}>
                    ✖ Exit Zen Mode
                </button>

                <div style={{ textAlign: "center", maxWidth: "600px", width: "90%" }}>
                    <h1 style={{ fontSize: "24px", marginBottom: "40px", opacity: 0.7, color: "var(--nf-text-secondary)" }}>
                        {currentTask || "Focus Session"}
                    </h1>
                    <div style={{ fontSize: "120px", fontWeight: 700, fontVariantNumeric: "tabular-nums", marginBottom: "40px", color: "var(--nf-text)" }}>
                        {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                    </div>
                    <div style={{ display: "flex", gap: "20px", justifyContent: "center" }}>
                        <button className="nf-btn nf-btn--primary" onClick={isActive ? pauseTimer : startTimer}
                            style={{ padding: "16px 40px", fontSize: "18px" }}>
                            {isActive ? "⏸ Pause" : "▶ Continue"}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Full page mode
    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "20px", alignItems: "center" }}>
            <div className="nf-page-header" style={{ width: "100%", maxWidth: "500px" }}>
                <h1 className="nf-page-header__title">Focus Mode</h1>
                <p className="nf-page-header__subtitle">Eliminate distractions. Focus on what matters.</p>
            </div>

            {/* Timer Card */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px", textAlign: "center", padding: "40px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
                    <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--nf-text)" }}>
                        🎯 Zen Space
                    </h2>
                    <button onClick={toggleZenMode} className="nf-btn nf-btn--ghost" style={{ fontSize: "12px" }}>
                        🖵 Fullscreen
                    </button>
                </div>

                {/* Circular Timer */}
                <div style={{ position: "relative", width: "260px", height: "260px", margin: "0 auto 32px" }}>
                    <svg width="260" height="260" style={{ transform: "rotate(-90deg)" }}>
                        <circle cx="130" cy="130" r="120" fill="none" stroke="rgba(124,92,252,0.1)" strokeWidth="6" />
                        <circle cx="130" cy="130" r="120" fill="none"
                            stroke="url(#focusGradient)" strokeWidth="6" strokeLinecap="round"
                            strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
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
                        position: "absolute", inset: 0,
                        display: "flex", flexDirection: "column",
                        alignItems: "center", justifyContent: "center",
                    }}>
                        <span style={{ fontSize: "56px", fontWeight: 700, fontVariantNumeric: "tabular-nums", color: "var(--nf-text)" }}>
                            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                        </span>
                    </div>
                </div>

                {/* Ambient Sounds */}
                <div style={{ display: "flex", gap: "8px", justifyContent: "center", marginBottom: "24px" }}>
                    {AMBIENT_SOUNDS.map(s => (
                        <button key={s.id}
                            className={`nf-btn ${currentSound === s.id ? "nf-btn--primary" : "nf-btn--ghost"}`}
                            onClick={() => toggleSound(s.id)}
                            style={{ fontSize: "12px", padding: "6px 12px" }}>
                            {s.label}
                        </button>
                    ))}
                </div>

                <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginBottom: "24px" }}>
                    {!isActive ? (
                        <button className="nf-btn nf-btn--primary" onClick={startTimer} style={{ minWidth: "120px" }}>
                            ▶ {progress > 0 ? "Resume" : "Start"}
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
                        <button key={p.label}
                            className={`nf-btn ${totalMinutes === p.min ? "nf-btn--primary" : "nf-btn--ghost"}`}
                            onClick={() => { setTotalMinutes(p.min); setMinutes(p.min); setSeconds(0); setIsActive(false); }}
                            style={{ fontSize: "12px", padding: "6px 14px" }}>
                            {p.min}m
                        </button>
                    ))}
                </div>
            </div>

            {/* Current Focus Task */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px" }}>
                <div className="nf-card__header">
                    <span className="nf-card__title">📝 Session Goal</span>
                </div>
                <input
                    className="nf-input"
                    value={currentTask}
                    onChange={(e) => setCurrentTask(e.target.value)}
                    placeholder="What are you working on?"
                    style={{ width: "100%" }}
                />
            </div>

            {/* Stats */}
            <div className="nf-card" style={{ width: "100%", maxWidth: "500px" }}>
                <div className="nf-card__header">
                    <span className="nf-card__title">📊 Focus Stats</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <div style={{
                        background: "var(--nf-bg-card)", border: "1px solid var(--nf-border)",
                        borderRadius: "var(--nf-radius-sm)", padding: "16px", textAlign: "center"
                    }}>
                        <div style={{ fontSize: "24px", fontWeight: 700, color: "var(--nf-accent)" }}>
                            {stats?.total_minutes || 0}m
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginTop: "4px" }}>Total Time</div>
                    </div>
                    <div style={{
                        background: "var(--nf-bg-card)", border: "1px solid var(--nf-border)",
                        borderRadius: "var(--nf-radius-sm)", padding: "16px", textAlign: "center"
                    }}>
                        <div style={{ fontSize: "24px", fontWeight: 700, color: "var(--nf-success)" }}>
                            {stats?.session_count || 0}
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginTop: "4px" }}>Sessions</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
