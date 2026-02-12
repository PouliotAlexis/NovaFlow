"use client";

import React from "react";

interface SidebarProps {
    activeView: string;
    onNavigate: (view: string) => void;
}

const NAV_ITEMS = [
    { id: "dashboard", icon: "🏠", label: "Dashboard" },
    { id: "chat", icon: "💬", label: "Chat AI" },
    { id: "tasks", icon: "✅", label: "Tâches" },
    { id: "calendar", icon: "📅", label: "Calendrier" },
    { id: "documents", icon: "📁", label: "Documents" },
];

const TOOLS = [
    { id: "dropzone", icon: "📥", label: "Drop Zone" },
    { id: "focus", icon: "🎯", label: "Focus Mode" },
];

export default function Sidebar({ activeView, onNavigate }: SidebarProps) {
    return (
        <aside className="nf-sidebar">
            {/* Logo */}
            <div className="nf-sidebar__logo">
                <div className="nf-sidebar__logo-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M18.5 2.5H14.5L9.5 14L8.5 14L8.5 2.5H4.5V21.5H8.5L13.5 10L14.5 10L14.5 21.5H18.5V2.5Z" fill="url(#paint0_linear)" />
                        <defs>
                            <linearGradient id="paint0_linear" x1="4.5" y1="2.5" x2="18.5" y2="21.5" gradientUnits="userSpaceOnUse">
                                <stop stopColor="#60A5FA" />
                                <stop offset="1" stopColor="#A78BFA" />
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <span className="nf-sidebar__logo-text">NovaFlow</span>
            </div>

            {/* Navigation */}
            <nav className="nf-sidebar__nav">
                <div className="nf-sidebar__section">Navigation</div>
                {NAV_ITEMS.map((item) => (
                    <button
                        key={item.id}
                        className={`nf-sidebar__item ${activeView === item.id ? "nf-sidebar__item--active" : ""
                            }`}
                        onClick={() => onNavigate(item.id)}
                    >
                        <span className="nf-sidebar__icon">{item.icon}</span>
                        {item.label}
                    </button>
                ))}

                <div className="nf-sidebar__section">Outils</div>
                {TOOLS.map((item) => (
                    <button
                        key={item.id}
                        className={`nf-sidebar__item ${activeView === item.id ? "nf-sidebar__item--active" : ""
                            }`}
                        onClick={() => onNavigate(item.id)}
                    >
                        <span className="nf-sidebar__icon">{item.icon}</span>
                        {item.label}
                    </button>
                ))}
            </nav>

            {/* Footer - AI Mode */}
            <div className="nf-sidebar__footer">
                <button
                    className={`nf-sidebar__item ${activeView === "settings" ? "nf-sidebar__item--active" : ""
                        }`}
                    onClick={() => onNavigate("settings")}
                >
                    <span className="nf-sidebar__icon">⚙️</span>
                    Réglages
                </button>
            </div>
        </aside>
    );
}
