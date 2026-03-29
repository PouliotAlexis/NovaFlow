import React, { useState, useEffect } from "react";
import CourseCard from "./CourseCard";
import { GraduationCap, RefreshCw, Plus } from "lucide-react";
import MoodleSyncDialog from "./MoodleSyncDialog";
import { api } from "@/services/api";

export default function MoodleDashboard() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);
  const [isConnected, setIsConnected] = useState<boolean | null>(null);

  const [expandedCourseId, setExpandedCourseId] = useState<string | null>(null);


  const fetchStatus = async () => {
    try {
      const res = await api.get("/api/v2/moodle/session/status");
      if (res.ok) {
        const data = await res.json();
        setIsConnected(data.connected);
      }
    } catch (err) {
      setIsConnected(false);
    }
  };

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/v2/moodle/courses");
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
    fetchStatus();
    
    // Refresh every 60s
    const interval = setInterval(() => {
      fetchCourses();
      fetchStatus();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const dashboardRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (expandedCourseId && dashboardRef.current) {
      dashboardRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [expandedCourseId]);

  const handleSyncStarted = () => {

    // Show a notification or just refresh periodically
    fetchCourses();
  };

  const handleChat = (id: string) => {
    window.location.href = `/chat/${id}`;
  };

  return (
    <div ref={dashboardRef} className="nf-moodle-dashboard nf-animate-in">

      <div className="nf-page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <GraduationCap size={28} color="var(--nf-accent)" />
          <h2 className="nf-page-header__title" style={{ margin: 0 }}>Mes Cours Moodle Docs</h2>
          {isConnected === false && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "12px" }}>
              <span className="nf-badge nf-badge--error" style={{ fontSize: "11px" }}>
                Session expirée
              </span>
              <button 
                className="nf-btn nf-btn--primary nf-btn--sm" 
                onClick={async (e) => {
                  const btn = e.currentTarget;
                  btn.disabled = true;
                  btn.innerHTML = '<span class="nf-spin">⏳</span>...';
                  try {
                    const res = await api.post("/api/v2/moodle/login");
                    const data = await res.json();
                    if (data.success) {
                      await fetchStatus();
                    } else if (data.bypass_url) {
                      if (confirm("Le serveur ne peut pas ouvrir de fenêtre Moodle (mode Cloud).\n\nVoulez-vous ouvrir la page de connexion manuellement dans un nouvel onglet ?\n\nAprès connexion, vous devrez utiliser l'extension NovaFlow pour synchroniser.")) {
                        window.open(data.bypass_url, "_blank");
                      }
                    } else if (data.error) {
                      let msg = `Erreur de connexion : ${data.error}`;
                      if (data.error.includes("BrowserType.launch") || data.error.includes("executable")) {
                        msg += "\n\n💡 Tip : Cette fonction nécessite un navigateur local. En ligne, utilisez l'extension NovaFlow pour capturer votre session Moodle.";
                      }
                      alert(msg);
                    } else {
                      alert("Échec de la connexion. Utilisez l'extension Moodle si vous êtes sur le Web.");
                    }
                  } catch (e: any) {
                    console.error("Login call failed", e);
                    alert("Erreur de communication avec le serveur.");
                  } finally {
                    btn.disabled = false;
                    btn.innerText = "Connecter";
                  }
                }}
                style={{ fontSize: "10px", height: "24px", padding: "0 10px", borderRadius: "12px" }}
                title="Ouvre une fenêtre pour rafraîchir la session Chrome"
              >
                Connecter
              </button>
            </div>
          )}
          {isConnected === true && (
            <span className="nf-badge nf-badge--success" style={{ marginLeft: "8px", fontSize: "12px" }}>
              Moodle : Connecté
            </span>
          )}
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
        {[...courses].sort((a, b) => (a.id === expandedCourseId ? -1 : b.id === expandedCourseId ? 1 : 0)).map(course => (
          <CourseCard 
            key={course.id}
            id={course.id}
            name={course.name}
            filesCount={course.filesCount}
            isExpanded={course.id === expandedCourseId}
            onToggleExpand={() => setExpandedCourseId(expandedCourseId === course.id ? null : course.id)}
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
