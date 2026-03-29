import React, { useState, useEffect } from "react";
import CourseCard from "./CourseCard";
import { GraduationCap, RefreshCw, Plus } from "lucide-react";
import MoodleSyncDialog from "./MoodleSyncDialog";
import { api } from "@/services/api";

interface MoodleStatus {
  connected: boolean;
  has_token?: boolean;
  has_sesskey?: boolean;
}

export default function MoodleDashboard() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);
  const [status, setStatus] = useState<MoodleStatus>({ connected: false });

  const [expandedCourseId, setExpandedCourseId] = useState<string | null>(null);


  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === "NOVAFLOW_MOODLE_SESSION") {
        const data = event.data.data;
        console.log("MoodleDashboard: Reçu session de l'extension !", data);
        
        // Sauver en localstorage pour les déploiements serverless (Vercel)
        localStorage.setItem("moodle_session", JSON.stringify(data));
        
        setStatus({
          connected: true,
          has_token: !!data.token,
          has_sesskey: !!data.sesskey
        });
      }
    };

    window.addEventListener("message", handleMessage);
    
    // Demander le statut actuel à l'extension
    window.postMessage({ type: "GET_NOVAFLOW_EXTENSION_STATUS" }, "*");

    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await api.get("/api/v2/moodle/session/status");
      if (res.ok) {
        const data = await res.json();
        
        // Si le serveur ne connaît pas la session, on vérifie notre localStorage
        if (!data.connected) {
           const local = localStorage.getItem("moodle_session");
           if (local) {
             const localData = JSON.parse(local);
             setStatus({
               connected: true,
               has_token: !!localData.token,
               has_sesskey: !!localData.sesskey
             });
             return;
           }
        }
        setStatus(data);
      }
    } catch (err) {
      console.warn("Erreur status Moodle backend, tentative localstorage...");
      const local = localStorage.getItem("moodle_session");
      if (local) {
        const localData = JSON.parse(local);
        setStatus({ connected: true, has_token: !!localData.token, has_sesskey: !!localData.sesskey });
      } else {
        setStatus({ connected: false });
      }
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
          {(!status.has_token && !status.has_sesskey) && (
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
                    // Récupérer le token local pour l'envoyer au serveur
                    const localSession = localStorage.getItem("moodle_session");
                    const token = localSession ? JSON.parse(localSession).token : null;
                    
                    const res = await api.post("/api/v2/moodle/login", { token });
                    const data = await res.json();
                    if (data.success) {
                      await fetchStatus();
                    } else if (data.bypass_url) {
                      if (confirm("L'extension NovaFlow a besoin d'ouvrir Moodle pour capturer votre session.\n\nVoulez-vous ouvrir l'onglet de connexion ?")) {
                        window.open(data.bypass_url, "_blank");
                        
                        // Active Polling: Check status every 2s
                        let checks = 0;
                        const pollInterval = setInterval(async () => {
                          checks++;
                          const resStatus = await api.get("/api/v2/moodle/session/status");
                          const statusData = await resStatus.json();
                          if (statusData.has_token || checks > 30) {
                            clearInterval(pollInterval);
                            await fetchStatus();
                            if (statusData.has_token) fetchCourses();
                          }
                        }, 2000);
                      }
                    }
                  } catch (e: any) {
                    console.error("Login call failed", e);
                  } finally {
                    btn.disabled = false;
                    btn.innerText = "Connecter";
                  }
                }}
                style={{ fontSize: "10px", height: "24px", padding: "0 10px", borderRadius: "12px" }}
              >
                Connecter
              </button>
            </div>
          )}
          {(status.has_sesskey && !status.has_token) && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "12px" }}>
              <span className="nf-badge nf-badge--primary" style={{ fontSize: "11px", background: "var(--nf-accent-glow)", color: "var(--nf-accent)" }}>
                ⏳ Génération du jeton...
              </span>
            </div>
          )}
          {status.has_token && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "12px" }}>
              <span className="nf-badge nf-badge--success" style={{ fontSize: "11px" }}>
                Session active
              </span>
            </div>
          )}
          {/* Bloc temporaire retiré car remplacé par status.has_token */}
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
