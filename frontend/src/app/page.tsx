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
import NotificationPanel from "@/components/NotificationPanel";
import AutomationStatus from "@/components/AutomationStatus";

export default function Home() {
  const [activeView, setActiveView] = useState("dashboard");

  // Rendu des onglets qui ne sont PAS pré-chargés (montage/démontage classique)
  const renderDynamicView = () => {
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
      case "documents":
        return <DocumentsView />;
      case "dropzone":
        return <DropZone />;
      case "focus":
        return <FocusMode />;
      case "settings":
        return <SettingsPanel />;
      case "tasks":
      case "calendar":
        return null; // Gérés par les composants persistants ci-dessous
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
        <header className="nf-header" style={{ position: "relative", zIndex: 50 }}>
          <div>
            <h1 className="nf-header__title">{title}</h1>
            <p className="nf-header__subtitle">{subtitle}</p>
          </div>
          <div className="nf-header__actions">
            <AutomationStatus />
            <div className="nf-ai-mode nf-ai-mode--local">
              <span className="nf-ai-mode__dot" />
              AI Locale
            </div>
            <NotificationPanel />
          </div>
        </header>

        {/* Content */}
        <div className="nf-content">
          {/* Composants persistants (toujours montés, masqués quand inactifs) */}
          <div style={{ display: activeView === "tasks" ? "block" : "none" }}>
            <TaskList />
          </div>
          <div style={{ display: activeView === "calendar" ? "block" : "none" }}>
            <CalendarView onNavigate={setActiveView} />
          </div>

          {/* Composants dynamiques (montés/démontés au besoin) */}
          {renderDynamicView()}
        </div>
      </main>
    </div>
  );
}
