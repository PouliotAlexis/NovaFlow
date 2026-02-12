"use client";

import React, { useState } from "react";
import Sidebar from "@/components/Sidebar";
import SmartFeed from "@/components/SmartFeed";
import TaskList from "@/components/TaskList";
import DropZone from "@/components/DropZone";
import ChatPanel from "@/components/ChatPanel";
import SettingsPanel from "@/components/SettingsPanel";
import CalendarView from "@/components/CalendarView";
import DocumentsView from "@/components/DocumentsView";
import FocusMode from "@/components/FocusMode";

export default function Home() {
  const [activeView, setActiveView] = useState("dashboard");

  const renderView = () => {
    switch (activeView) {
      case "dashboard":
        return (
          <div className="nf-dashboard">
            <SmartFeed />
            <TaskList />
            <DropZone />
            <div className="nf-dashboard__full">
              <ChatPanel />
            </div>
          </div>
        );
      case "chat":
        return <ChatPanel />;
      case "tasks":
        return <TaskList />;
      case "calendar":
        return <CalendarView />;
      case "documents":
        return <DocumentsView />;
      case "dropzone":
        return <DropZone />;
      case "focus":
        return <FocusMode />;
      case "settings":
        return <SettingsPanel />;
      default:
        return (
          <div className="nf-card nf-animate-in" style={{ textAlign: "center", padding: "60px" }}>
            <span style={{ fontSize: "48px", display: "block", marginBottom: "16px" }}>🚧</span>
            <h2 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "8px" }}>
              En construction
            </h2>
            <p style={{ color: "var(--nf-text-muted)", fontSize: "14px" }}>
              Cette section arrive bientôt !
            </p>
          </div>
        );
    }
  };

  const getPageTitle = () => {
    const titles: Record<string, { title: string; subtitle: string }> = {
      dashboard: { title: "Dashboard", subtitle: "Vue d'ensemble de ta journée" },
      chat: { title: "Chat AI", subtitle: "Pose tes questions à l'IA" },
      tasks: { title: "Tâches", subtitle: "Gère tes priorités" },
      calendar: { title: "Calendrier", subtitle: "Tes échéances et événements" },
      documents: { title: "Documents", subtitle: "Tes fichiers analysés" },
      dropzone: { title: "Drop Zone", subtitle: "Importe de nouveaux fichiers" },
      focus: { title: "Focus Mode", subtitle: "Concentration maximale" },
      settings: { title: "Réglages", subtitle: "Configuration de NovaFlow" },
    };
    return titles[activeView] || { title: activeView, subtitle: "" };
  };

  const { title, subtitle } = getPageTitle();

  return (
    <div className="nf-layout">
      <Sidebar activeView={activeView} onNavigate={setActiveView} />

      <main className="nf-main">
        {/* Header */}
        <header className="nf-header">
          <div>
            <h1 className="nf-header__title">{title}</h1>
            <p className="nf-header__subtitle">{subtitle}</p>
          </div>
          <div className="nf-header__actions">
            <div className="nf-ai-mode nf-ai-mode--local">
              <span className="nf-ai-mode__dot" />
              AI Locale
            </div>
            <button className="nf-btn--icon" title="Notifications">🔔</button>
          </div>
        </header>

        {/* Content */}
        <div className="nf-content">
          {renderView()}
        </div>
      </main>
    </div>
  );
}
