"use client";

import React, { useState, useEffect, useRef } from "react";

export default function SettingsPanel() {
    const [aiMode, setAiMode] = useState<"local" | "cloud">("local");
    const [profile, setProfile] = useState<"student" | "pro" | "personal">("student");
    const [googleAccounts, setGoogleAccounts] = useState<string[]>([]);
    const [microsoftAccounts, setMicrosoftAccounts] = useState<string[]>([]);
    const prevAccountCount = useRef<number | null>(null);
    const prevMsAccountCount = useRef<number | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchGoogleAccounts = async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/google/accounts`);
            if (res.ok) {
                const data = await res.json();
                const accounts = data.accounts || [];
                setGoogleAccounts(accounts);

                if (prevAccountCount.current !== null && accounts.length !== prevAccountCount.current) {
                    window.dispatchEvent(new CustomEvent("novaflow-account-changed"));
                }
                prevAccountCount.current = accounts.length;
            }
        } catch (err) {
            console.error("Error fetching accounts:", err);
        }
    };

    const fetchMicrosoftAccounts = async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/microsoft/accounts`);
            if (res.ok) {
                const data = await res.json();
                const accounts = data.accounts || [];
                setMicrosoftAccounts(accounts);

                if (prevMsAccountCount.current !== null && accounts.length !== prevMsAccountCount.current) {
                    window.dispatchEvent(new CustomEvent("novaflow-account-changed"));
                }
                prevMsAccountCount.current = accounts.length;
            }
        } catch (err) {
            console.error("Error fetching Microsoft accounts:", err);
        }
    };

    useEffect(() => {
        fetchGoogleAccounts();
        fetchMicrosoftAccounts();
    }, []);

    useEffect(() => {
        if (window.location.hash === "#connections") {
            setTimeout(() => {
                document.getElementById("connections")?.scrollIntoView({ behavior: "smooth" });
                window.history.replaceState(null, "", window.location.pathname);
            }, 100);
        }
    }, []);

    const connectGoogle = async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/google/login`);
            if (res.ok) {
                const data = await res.json();
                window.open(data.url, "_blank", "width=600,height=600");
                const onFocus = () => {
                    setTimeout(fetchGoogleAccounts, 1500);
                    window.removeEventListener("focus", onFocus);
                };
                window.addEventListener("focus", onFocus);
            }
        } catch (err) {
            alert("Error connecting to Google");
        }
    };

    const disconnectGoogle = async (email: string) => {
        if (!confirm(`Disconnect account ${email}?`)) return;
        try {
            const res = await fetch(`${API_URL}/api/auth/google/accounts/${email}`, { method: "DELETE" });
            if (res.ok) {
                fetchGoogleAccounts();
            }
        } catch (err) {
            alert("Error disconnecting");
        }
    };

    const connectMicrosoft = async () => {
        try {
            const res = await fetch(`${API_URL}/api/auth/microsoft/login`);
            if (res.ok) {
                const data = await res.json();
                window.open(data.url, "_blank", "width=600,height=700");
                const onFocus = () => {
                    setTimeout(fetchMicrosoftAccounts, 2000);
                    window.removeEventListener("focus", onFocus);
                };
                window.addEventListener("focus", onFocus);
            }
        } catch (err) {
            alert("Error connecting to Microsoft");
        }
    };

    const disconnectMicrosoft = async (email: string) => {
        if (!confirm(`Disconnect Microsoft account ${email}?`)) return;
        try {
            const res = await fetch(`${API_URL}/api/auth/microsoft/accounts/${email}`, { method: "DELETE" });
            if (res.ok) {
                fetchMicrosoftAccounts();
            }
        } catch (err) {
            alert("Error disconnecting Microsoft");
        }
    };

    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div className="nf-page-header">
                <h1 className="nf-page-header__title">Settings</h1>
                <p className="nf-page-header__subtitle">Customize your NovaFlow experience</p>
            </div>

            {/* Profile Selection */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">👤 Profile</span>
                </div>

                <div style={{ display: "flex", gap: "12px" }}>
                    {[
                        { id: "student" as const, icon: "🎓", label: "Student" },
                        { id: "pro" as const, icon: "💼", label: "Professional" },
                        { id: "personal" as const, icon: "🏠", label: "Personal" },
                    ].map((p) => (
                        <button
                            key={p.id}
                            className={`nf-btn ${profile === p.id ? "nf-btn--primary" : "nf-btn--ghost"}`}
                            onClick={() => setProfile(p.id)}
                            style={{ flex: 1, justifyContent: "center" }}
                        >
                            <span>{p.icon}</span>
                            {p.label}
                        </button>
                    ))}
                </div>

                <p style={{
                    fontSize: "13px",
                    color: "var(--nf-text-muted)",
                    marginTop: "12px",
                    lineHeight: "1.5",
                }}>
                    {profile === "student" && "Student Mode: Prioritizes exam dates, assignments, and course notes."}
                    {profile === "pro" && "Professional Mode: Prioritizes meetings, critical emails, and project tasks."}
                    {profile === "personal" && "Personal Mode: Prioritizes habits, finances, and appointments."}
                </p>
            </div>

            {/* AI Mode */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">🧠 AI Engine</span>
                    <div className={`nf-ai-mode nf-ai-mode--${aiMode}`}>
                        <span className="nf-ai-mode__dot" />
                        {aiMode === "local" ? "Local (Ollama)" : "Cloud (OpenAI)"}
                    </div>
                </div>

                <div style={{ display: "flex", gap: "12px" }}>
                    <button
                        className={`nf-btn ${aiMode === "local" ? "nf-btn--primary" : "nf-btn--ghost"}`}
                        onClick={() => setAiMode("local")}
                        style={{ flex: 1, justifyContent: "center" }}
                    >
                        🏠 Local (Private)
                    </button>
                    <button
                        className={`nf-btn ${aiMode === "cloud" ? "nf-btn--primary" : "nf-btn--ghost"}`}
                        onClick={() => setAiMode("cloud")}
                        style={{ flex: 1, justifyContent: "center" }}
                    >
                        ☁️ Cloud
                    </button>
                </div>

                <div style={{
                    marginTop: "16px",
                    padding: "12px 16px",
                    background: aiMode === "local"
                        ? "rgba(34, 197, 94, 0.1)"
                        : "rgba(59, 130, 246, 0.1)",
                    borderRadius: "var(--nf-radius-sm)",
                    fontSize: "13px",
                    lineHeight: "1.6",
                    color: "var(--nf-text-secondary)",
                    border: "1px solid " + (aiMode === "local" ? "rgba(34, 197, 94, 0.2)" : "rgba(59, 130, 246, 0.2)"),
                }}>
                    {aiMode === "local" ? (
                        <>
                            <strong style={{ color: "var(--nf-success)" }}>🔒 Bunker Mode</strong>
                            <br />
                            All data stays on your PC. Nothing leaves.
                            <br />
                            Model: Llama 3 via Ollama (localhost:11434)
                        </>
                    ) : (
                        <>
                            <strong style={{ color: "var(--nf-info)" }}>🛡️ Secure Cloud Mode</strong>
                            <br />
                            Sensitive data is redacted BEFORE sending (Reversible Redaction).
                            <br />
                            Names, emails, and amounts are replaced with tokens.
                        </>
                    )}
                </div>
            </div>

            {/* Connections */}
            <div className="nf-card" id="connections">
                <div className="nf-card__header">
                    <span className="nf-card__title">🔗 Connections</span>
                </div>

                <div className="nf-task-list">
                    {/* Google Section */}
                    <div className="nf-task" style={{ flexDirection: "column", alignItems: "flex-start", gap: "12px" }}>
                        <div style={{ display: "flex", width: "100%", alignItems: "center", gap: "12px" }}>
                            <span style={{ fontSize: "22px" }}>🔵</span>
                            <div className="nf-task__content">
                                <div className="nf-task__title">Google</div>
                                <div className="nf-task__meta">Calendar, Gmail, Drive (Multi-account)</div>
                            </div>
                            <button className="nf-btn nf-btn--primary" style={{ fontSize: "12px" }} onClick={connectGoogle}>
                                {googleAccounts.length > 0 ? "Add Account" : "Connect"}
                            </button>
                        </div>

                        {googleAccounts.length > 0 && (
                            <div style={{ width: "100%", paddingLeft: "34px", display: "flex", flexDirection: "column", gap: "6px" }}>
                                {googleAccounts.map(email => (
                                    <div key={email} style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        padding: "6px 10px",
                                        background: "var(--nf-bg-card)",
                                        borderRadius: "var(--nf-radius-xs)",
                                        border: "1px solid var(--nf-border)",
                                        fontSize: "12px"
                                    }}>
                                        <span style={{ color: "var(--nf-text-secondary)" }}>📧 {email}</span>
                                        <button
                                            onClick={() => disconnectGoogle(email)}
                                            style={{ background: "transparent", border: "none", color: "var(--nf-danger)", cursor: "pointer", fontSize: "11px", fontWeight: 500 }}
                                        >
                                            Disconnect
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Microsoft Section */}
                    <div className="nf-task" style={{ flexDirection: "column", alignItems: "flex-start", gap: "12px" }}>
                        <div style={{ display: "flex", width: "100%", alignItems: "center", gap: "12px" }}>
                            <span style={{ fontSize: "22px" }}>🟦</span>
                            <div className="nf-task__content">
                                <div className="nf-task__title">Microsoft</div>
                                <div className="nf-task__meta">Outlook Calendar, To Do, OneDrive</div>
                            </div>
                            <button className="nf-btn nf-btn--primary" style={{ fontSize: "12px" }} onClick={connectMicrosoft}>
                                {microsoftAccounts.length > 0 ? "Add Account" : "Connect"}
                            </button>
                        </div>

                        {microsoftAccounts.length > 0 && (
                            <div style={{ width: "100%", paddingLeft: "34px", display: "flex", flexDirection: "column", gap: "6px" }}>
                                {microsoftAccounts.map(email => (
                                    <div key={email} style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        padding: "6px 10px",
                                        background: "var(--nf-bg-card)",
                                        borderRadius: "var(--nf-radius-xs)",
                                        border: "1px solid var(--nf-border)",
                                        fontSize: "12px"
                                    }}>
                                        <span style={{ color: "var(--nf-text-secondary)" }}>📧 {email}</span>
                                        <button
                                            onClick={() => disconnectMicrosoft(email)}
                                            style={{ background: "transparent", border: "none", color: "var(--nf-danger)", cursor: "pointer", fontSize: "11px", fontWeight: 500 }}
                                        >
                                            Disconnect
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Moodle Placeholder */}
                    <div className="nf-task">
                        <span style={{ fontSize: "22px" }}>🟠</span>
                        <div className="nf-task__content">
                            <div className="nf-task__title">Moodle</div>
                            <div className="nf-task__meta">Courses, assignments, grades</div>
                        </div>
                        <button className="nf-btn nf-btn--ghost" style={{ fontSize: "12px" }}>
                            Connect
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
