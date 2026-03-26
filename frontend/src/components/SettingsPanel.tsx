"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
    User, GraduationCap, Briefcase, Home, Brain, 
    Cloud, Mail, Calendar, Link, Plus, Trash2, Shield 
} from "lucide-react";
import { api } from "@/services/api";

export default function SettingsPanel() {
    const [aiMode, setAiMode] = useState<"local" | "cloud">("local");
    const [profile, setProfile] = useState<"student" | "pro" | "personal">("student");
    const [googleAccounts, setGoogleAccounts] = useState<string[]>([]);
    const [microsoftAccounts, setMicrosoftAccounts] = useState<string[]>([]);
    const [moodleUrls, setMoodleUrls] = useState<string[]>([]);
    const [newMoodleUrl, setNewMoodleUrl] = useState<string>("");
    const [isSavingMoodle, setIsSavingMoodle] = useState(false);
    const prevAccountCount = useRef<number | null>(null);
    const prevMsAccountCount = useRef<number | null>(null);


    const fetchGoogleAccounts = async () => {
        try {
            const res = await api.get("/api/auth/google/accounts");
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
            const res = await api.get("/api/auth/microsoft/accounts");
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

    const fetchMoodleSettings = async () => {
        try {
            const res = await api.get("/api/settings/moodle");
            if (res.ok) {
                const data = await res.json();
                setMoodleUrls(data.urls || (data.url ? [data.url] : []));
            }
        } catch (err) {
            console.error("Error fetching Moodle settings:", err);
        }
    };

    const addMoodleUrl = async () => {
        if (!newMoodleUrl.trim()) return;
        setIsSavingMoodle(true);
        try {
            const res = await api.post("/api/settings/moodle", { url: newMoodleUrl.trim() });
            if (res.ok) {
                const data = await res.json();
                setMoodleUrls(data.urls || []);
                setNewMoodleUrl("");
                window.dispatchEvent(new CustomEvent("novaflow-account-changed"));
            }
        } catch (err) {
            alert("Erreur lors de l'ajout de l'URL Moodle");
        }
        setIsSavingMoodle(false);
    };

    const removeMoodleUrl = async (url: string) => {
        try {
            const res = await api.delete(`/api/settings/moodle?url=${encodeURIComponent(url)}`);
            if (res.ok) {
                const data = await res.json();
                setMoodleUrls(data.urls || []);
                window.dispatchEvent(new CustomEvent("novaflow-account-changed"));
            }
        } catch (err) {
            alert("Erreur lors de la suppression");
        }
    };

    useEffect(() => {
        fetchGoogleAccounts();
        fetchMicrosoftAccounts();
        fetchMoodleSettings();
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
            const res = await api.get("/api/auth/google/login");
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
            const res = await api.delete(`/api/auth/google/accounts/${email}`);
            if (res.ok) {
                fetchGoogleAccounts();
            }
        } catch (err) {
            alert("Error disconnecting");
        }
    };

    const connectMicrosoft = async () => {
        try {
            const res = await api.get("/api/auth/microsoft/login");
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
            const res = await api.delete(`/api/auth/microsoft/accounts/${email}`);
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
                    <span className="nf-card__title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <User size={18} color="var(--nf-accent)" /> Profile
                    </span>
                </div>

                <div style={{ display: "flex", gap: "12px" }}>
                    {[
                        { id: "student" as const, icon: <GraduationCap size={16} />, label: "Student" },
                        { id: "pro" as const, icon: <Briefcase size={16} />, label: "Professional" },
                        { id: "personal" as const, icon: <Home size={16} />, label: "Personal" },
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
                    <span className="nf-card__title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Brain size={18} color="var(--nf-accent)" /> AI Engine
                    </span>
                    <div className={`nf-ai-mode nf-ai-mode--${aiMode}`}>
                        <span className="nf-ai-mode__dot" />
                        {aiMode === "local" ? "Local (Ollama)" : "Cloud (OpenAI)"}
                    </div>
                </div>

                <div style={{ display: "flex", gap: "12px" }}>
                    <button
                        className={`nf-btn ${aiMode === "local" ? "nf-btn--primary" : "nf-btn--ghost"}`}
                        onClick={() => setAiMode("local")}
                        style={{ flex: 1, justifyContent: "center", gap: "8px" }}
                    >
                        <Home size={16} /> Local (Private)
                    </button>
                    <button
                        className={`nf-btn ${aiMode === "cloud" ? "nf-btn--primary" : "nf-btn--ghost"}`}
                        onClick={() => setAiMode("cloud")}
                        style={{ flex: 1, justifyContent: "center", gap: "8px" }}
                    >
                        <Cloud size={16} /> Cloud
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
                            <strong style={{ color: "var(--nf-success)", display: "flex", alignItems: "center", gap: "4px" }}>
                                <Shield size={14} /> Bunker Mode
                            </strong>
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
                    <span className="nf-card__title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Link size={18} color="var(--nf-accent)" /> Connections
                    </span>
                </div>

                <div className="nf-task-list">
                    {/* Google Section */}
                    <div className="nf-task" style={{ flexDirection: "column", alignItems: "flex-start", gap: "12px" }}>
                        <div style={{ display: "flex", width: "100%", alignItems: "center", gap: "12px" }}>
                            <span style={{ width: "22px", height: "22px", display: "inline-flex" }}><svg viewBox="0 0 24 24" width="22" height="22"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" /></svg></span>
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
                                        <span style={{ color: "var(--nf-text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
                                            <Mail size={12} /> {email}
                                        </span>
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
                            <span style={{ width: "22px", height: "22px", display: "inline-flex" }}><svg viewBox="0 0 24 24" width="22" height="22"><rect x="1" y="1" width="10" height="10" fill="#F25022" /><rect x="13" y="1" width="10" height="10" fill="#7FBA00" /><rect x="1" y="13" width="10" height="10" fill="#00A4EF" /><rect x="13" y="13" width="10" height="10" fill="#FFB900" /></svg></span>
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

                    {/* Moodle Section */}
                    <div className="nf-task" style={{ flexDirection: "column", alignItems: "flex-start", gap: "12px" }}>
                        <div style={{ display: "flex", width: "100%", alignItems: "center", gap: "12px" }}>
                            <span style={{ width: "22px", height: "22px", display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: "4px", background: "#f98012", color: "#fff", fontSize: "14px", fontWeight: 700 }}>M</span>
                            <div className="nf-task__content">
                                <div className="nf-task__title">Moodle (Via Flux RSS / iCal)</div>
                                <div className="nf-task__meta">Échéances de devoirs et événements</div>
                            </div>
                        </div>

                        {moodleUrls.length > 0 && (
                            <div style={{ width: "100%", paddingLeft: "34px", display: "flex", flexDirection: "column", gap: "6px" }}>
                                {moodleUrls.map((url, i) => (
                                    <div key={i} style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        padding: "6px 10px",
                                        background: "var(--nf-bg-card)",
                                        borderRadius: "var(--nf-radius-xs)",
                                        border: "1px solid var(--nf-border)",
                                        fontSize: "12px"
                                    }}>
                                        <span style={{ color: "var(--nf-text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "80%", display: "flex", alignItems: "center", gap: "6px" }}>
                                            <Calendar size={12} /> Calendrier {i + 1} — {url.includes("usherbrooke") ? "UdeS" : url.split("/")[2] || "Moodle"}
                                        </span>
                                        <button
                                            onClick={() => removeMoodleUrl(url)}
                                            style={{ background: "transparent", border: "none", color: "var(--nf-danger)", cursor: "pointer", fontSize: "11px", fontWeight: 500 }}
                                        >
                                            Supprimer
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div style={{ width: "100%", paddingLeft: "34px", display: "flex", gap: "8px", alignItems: "center" }}>
                            <input
                                type="text"
                                value={newMoodleUrl}
                                onChange={(e) => setNewMoodleUrl(e.target.value)}
                                placeholder="Collez l'URL d'exportation Moodle (iCal) ici"
                                onKeyDown={(e) => e.key === "Enter" && addMoodleUrl()}
                                style={{
                                    flex: 1,
                                    padding: "8px 12px",
                                    borderRadius: "var(--nf-radius-xs)",
                                    border: "1px solid var(--nf-border)",
                                    background: "var(--nf-bg-secondary)",
                                    color: "var(--nf-text)",
                                    fontSize: "13px"
                                }}
                            />
                            <button
                                className="nf-btn nf-btn--primary"
                                style={{ fontSize: "12px", padding: "8px 16px" }}
                                onClick={addMoodleUrl}
                                disabled={isSavingMoodle}
                            >
                                {isSavingMoodle ? "..." : "Ajouter"}
                            </button>
                        </div>
                        <p style={{ paddingLeft: "34px", fontSize: "11px", color: "var(--nf-text-muted)", margin: 0 }}>
                            Allez dans Moodle &gt; Calendrier &gt; Exporter le calendrier et collez le lien ci-dessus. Vous pouvez ajouter plusieurs calendriers.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
