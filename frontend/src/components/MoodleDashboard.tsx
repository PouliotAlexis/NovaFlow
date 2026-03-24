import React, { useState, useEffect } from "react";
import CourseCard from "./CourseCard";
import { GraduationCap, RefreshCw, Plus } from "lucide-react";
import MoodleSyncDialog from "./MoodleSyncDialog";

export default function MoodleDashboard() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v2/moodle/courses`);
      if (res.ok) {
        const data = await res.json();
        setCourses(data);
      }
    } catch (err) {
      console.error("Error fetching courses", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
    
    // Refresh every 30s to see sync progress
    const interval = setInterval(fetchCourses, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSyncStarted = () => {
    // Show a notification or just refresh periodically
    fetchCourses();
  };

  const handleChat = (id: string) => {
    window.location.href = `/chat/${id}`;
  };

  return (
    <div className="nf-moodle-dashboard nf-animate-in">
      <div className="nf-page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <GraduationCap size={28} color="var(--nf-accent)" />
          <h2 className="nf-page-header__title" style={{ margin: 0 }}>Mes Cours Moodle Docs</h2>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button 
            className="nf-btn nf-btn--primary"
            onClick={() => setIsSyncDialogOpen(true)}
          >
            <Plus size={16} />
            Nouvelle Synchro
          </button>
          <button 
            className="nf-btn nf-btn--icon"
            onClick={fetchCourses}
            disabled={loading}
            title="Rafraîchir"
          >
            <RefreshCw size={16} className={loading ? "nf-spin" : ""} />
          </button>
        </div>
      </div>

      <div className="nf-course-grid">
        {courses.length === 0 && !loading && (
          <div className="nf-empty-state" style={{ gridColumn: "1 / -1", padding: "40px" }}>
            <p style={{ color: "var(--nf-text-muted)" }}>Aucun document Moodle synchronisé. Cliquez sur "Nouvelle Synchro" pour commencer.</p>
          </div>
        )}
        {courses.map(course => (
          <CourseCard 
            key={course.id}
            id={course.id}
            name={course.name}
            filesCount={course.filesCount}
            onSync={() => setIsSyncDialogOpen(true)}
            onOpenChat={handleChat}
          />
        ))}
      </div>

      <MoodleSyncDialog 
        isOpen={isSyncDialogOpen} 
        onClose={() => setIsSyncDialogOpen(false)}
        onSyncStarted={handleSyncStarted}
      />
    </div>
  );
}
