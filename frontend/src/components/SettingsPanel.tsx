"use client";

import React, { useState } from "react";

export default function SettingsPanel() {
    const [aiMode, setAiMode] = useState<"local" | "cloud">("local");
    const [profile, setProfile] = useState<"student" | "pro" | "personal">("student");

    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Profile Selection */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">👤 Profil</span>
                </div>

                <div style={{ display: "flex", gap: "12px" }}>
                    {[
                        { id: "student" as const, icon: "🎓", label: "Étudiant" },
                        { id: "pro" as const, icon: "💼", label: "Professionnel" },
                        { id: "personal" as const, icon: "🏠", label: "Personnel" },
                    ].map((p) => (
                        <button
                            key={p.id}
                            className={`nf-btn ${profile === p.id ? "nf-btn--primary" : "nf-btn--ghost"
                                }`}
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
                    {profile === "student" && "Mode Étudiant : Priorité aux dates d'examens, devoirs et notes de cours."}
                    {profile === "pro" && "Mode Professionnel : Priorité aux réunions, emails critiques et tâches projet."}
                    {profile === "personal" && "Mode Personnel : Priorité aux habitudes, finances et rendez-vous."}
                </p>
            </div>

            {/* AI Mode */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">🧠 Moteur IA</span>
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
                        🏠 Local (Privé)
                    </button>
                    <button
                        className={`nf-btn ${aiMode === "cloud" ? "nf-btn--primary" : "nf-btn--ghost"}`}
                        onClick={() => setAiMode("cloud")}
                        style={{ flex: 1, justifyContent: "center" }}
                    >
                        ☁️ Cloud (Censuré)
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
                }}>
                    {aiMode === "local" ? (
                        <>
                            <strong style={{ color: "var(--nf-success)" }}>🔒 Mode Bunker</strong>
                            <br />
                            Toutes les données restent sur ton PC. Rien ne sort.
                            <br />
                            Modèle : Llama 3 via Ollama (localhost:11434)
                        </>
                    ) : (
                        <>
                            <strong style={{ color: "var(--nf-info)" }}>🛡️ Mode Cloud Sécurisé</strong>
                            <br />
                            Les données sensibles sont censurées AVANT l&apos;envoi (Reversible Redaction).
                            <br />
                            Les noms, emails et montants sont remplacés par des tokens.
                        </>
                    )}
                </div>
            </div>

            {/* Connections */}
            <div className="nf-card">
                <div className="nf-card__header">
                    <span className="nf-card__title">🔗 Connexions</span>
                </div>

                <div className="nf-task-list">
                    {[
                        { icon: "🔵", name: "Google", desc: "Calendar, Gmail, Drive", status: "non connecté" },
                        { icon: "🟦", name: "Microsoft", desc: "Outlook, OneDrive, Teams", status: "non connecté" },
                        { icon: "🟠", name: "Moodle", desc: "Cours, devoirs, notes", status: "non connecté" },
                    ].map((conn) => (
                        <div key={conn.name} className="nf-task">
                            <span style={{ fontSize: "24px" }}>{conn.icon}</span>
                            <div className="nf-task__content">
                                <div className="nf-task__title">{conn.name}</div>
                                <div className="nf-task__meta">{conn.desc}</div>
                            </div>
                            <button className="nf-btn nf-btn--ghost" style={{ fontSize: "12px" }}>
                                Connecter
                            </button>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
