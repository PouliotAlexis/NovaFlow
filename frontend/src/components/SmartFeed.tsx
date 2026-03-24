"use client";

import React, { useState, useEffect } from "react";
import { Sparkles } from "lucide-react";

export default function SmartFeed() {
    const [greeting, setGreeting] = useState("");
    const [dateStr, setDateStr] = useState("");

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
        <div className="nf-smart-feed nf-animate-in">
            <div className="nf-smart-feed__label">
                <Sparkles size={14} style={{ marginRight: '6px' }} />
                Smart Feed
            </div>
            <div className="nf-smart-feed__greeting">
                {greeting || "Bonjour"}, Alexis
            </div>
            <p className="nf-smart-feed__summary">
                {dateStr
                    ? `Here's your daily summary for ${dateStr}.`
                    : "Loading..."}
            </p>
        </div>
    );
}
