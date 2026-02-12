"use client";

import React, { useState, useEffect } from "react";

export default function SmartFeed() {
    const [greeting, setGreeting] = useState("");
    const [dateStr, setDateStr] = useState("");

    // Calcul côté client uniquement pour éviter le mismatch d'hydratation
    useEffect(() => {
        const now = new Date();
        setGreeting(
            now.getHours() < 12
                ? "Bon matin"
                : now.getHours() < 18
                    ? "Bon après-midi"
                    : "Bonsoir"
        );
        setDateStr(
            now.toLocaleDateString("fr-CA", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            })
        );
    }, []);

    return (
        <div className="nf-card nf-smart-feed nf-animate-in">
            <div className="nf-smart-feed__greeting">
                {greeting || "Bonjour"}, Alexis 👋
            </div>
            <p className="nf-smart-feed__summary">
                {dateStr
                    ? `Aujourd'hui c'est ${dateStr}. Voici ton résumé : `
                    : "Chargement... "}
                Connecte tes comptes et glisse des documents dans la Drop Zone pour que
                NovaFlow commence à organiser ta journée.
            </p>

            <div className="nf-smart-feed__stats">
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-accent-primary)" }}>0</span>
                    <span className="nf-stat__label">Tâches</span>
                </div>
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-warning)" }}>0</span>
                    <span className="nf-stat__label">Échéances</span>
                </div>
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-success)" }}>0</span>
                    <span className="nf-stat__label">Complétées</span>
                </div>
                <div className="nf-stat">
                    <span className="nf-stat__value" style={{ color: "var(--nf-info)" }}>0</span>
                    <span className="nf-stat__label">Documents</span>
                </div>
            </div>
        </div>
    );
}
