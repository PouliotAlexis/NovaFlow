"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import SmartFeed from "@/components/SmartFeed";
import DailySummary from "@/components/DailySummary";
import ProductivityTrend from "@/components/ProductivityTrend";
import WeatherWidget from "@/components/WeatherWidget";
import TaskList from "@/components/TaskList";
import DropZone from "@/components/DropZone";
import MiniCalendar from "@/components/MiniCalendar";
import ChatPanel from "@/components/ChatPanel";
import FocusMode from "@/components/FocusMode";
import CalendarView from "@/components/CalendarView";
import DocumentsView from "@/components/DocumentsView";
import SettingsPanel from "@/components/SettingsPanel";
import NotificationPanel from "@/components/NotificationPanel";
import AutomationStatus from "@/components/AutomationStatus";
import MoodleDashboard from "@/components/MoodleDashboard";
import { Hammer } from "lucide-react";

export default function Home() {
  const [activeView, setActiveView] = useState("dashboard");
  
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const view = params.get("view");
    if (view) {
      setActiveView(view);
    }
  }, []);

  const renderDynamicView = () => {
    switch (activeView) {
      case "dashboard":
        return null; // Handled by persistent view
      case "chat":
        return <ChatPanel />;
      case "documents":
        return <DocumentsView />;
      case "focus":
        return <FocusMode />;
      case "settings":
        return <SettingsPanel />;
      case "courses":
        return (
          <div style={{ marginTop: "20px" }}>
            <MoodleDashboard />
          </div>
        );
      case "tasks":
      case "calendar":
        return null;
      default:
        return (
          <div className="nf-card nf-animate-in" style={{ textAlign: "center", padding: "60px" }}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px", opacity: 0.5 }}>
              <Hammer size={48} strokeWidth={1} />
            </div>
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

  return (
    <div className="nf-layout">
      <Sidebar activeView={activeView} onNavigate={setActiveView} />

      <main className="nf-main">
        {/* Compact header with actions only */}
        <header className="nf-header" style={{ position: "relative", zIndex: 50 }}>
          <div className="nf-header__actions">
            <AutomationStatus />
            <div className="nf-ai-mode nf-ai-mode--local">
              <span className="nf-ai-mode__dot" />
              AI Local
            </div>
            <NotificationPanel />
          </div>
        </header>

        {/* Content */}
        <div className="nf-content">
          {/* Persistent tabs (always mounted, hidden when inactive) */}
          <div style={{ display: activeView === "dashboard" ? "block" : "none" }}>
            <div className="nf-dashboard">
              {/* Row 1: Greeting */}
              <SmartFeed />

              {/* Row 2: Stats */}
              <DailySummary />
              <ProductivityTrend />
              <WeatherWidget />

              {/* Row 3: Tools */}
              <DropZone />
              <TaskList compact onNavigate={setActiveView} />
              <MiniCalendar />

              {/* Row 4: Focus + Chat */}
              <div className="nf-dashboard__full" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <FocusMode compact />
                <ChatPanel compact />
              </div>
            </div>
          </div>
          <div style={{ display: activeView === "tasks" ? "block" : "none" }}>
            <TaskList />
          </div>
          <div style={{ display: activeView === "calendar" ? "block" : "none" }}>
            <CalendarView onNavigate={setActiveView} />
          </div>

          {/* Dynamic views (mounted only when active) */}
          {renderDynamicView()}
        </div>
      </main>
    </div>
  );
}
