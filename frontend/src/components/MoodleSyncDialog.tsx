"use client";

import React, { useState, useEffect } from "react";
import { X, Lock, Globe, User, RefreshCw, Cpu } from "lucide-react";

interface MoodleSyncDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncStarted: () => void;
}

export default function MoodleSyncDialog({ isOpen, onClose, onSyncStarted }: MoodleSyncDialogProps) {
  const [authMode, setAuthMode] = useState<"credentials" | "token">("credentials");
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [captureSuccess, setCaptureSuccess] = useState(false);
  const [error, setError] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  // Pré-remplir avec l'URL Moodle déjà configurée dans les settings
  useEffect(() => {
    if (!isOpen) return;
    fetch(`${API_URL}/api/settings/moodle`)
      .then((r) => r.json())
      .then((data) => {
        const first = data.urls?.[0] || data.url || "";
        if (first) setUrl(first);
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const isCalendarFeedUrl = (inputUrl: string) => {
    const u = (inputUrl || "").toLowerCase();
    return (
      u.includes("export_execute.php") ||
      u.includes("calendar/export.php") ||
      u.endsWith(".ics") ||
      u.includes("authtoken=")
    );
  };

  const handleSync = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Nettoyage de l'URL pour n'avoir que la racine (ex: https://moodle.usherbrooke.ca)
      let normalizedUrl = url.trim();
      try {
        const parsed = new URL(normalizedUrl);
        normalizedUrl = `${parsed.protocol}//${parsed.hostname}${parsed.port ? ':' + parsed.port : ''}`;
      } catch (e) {
        // En cas d'URL invalide, on laisse tel quel pour le backend
      }

      const body: any = { url: normalizedUrl };
      const isNative = authMode === "credentials";

      if (!isNative) {
        body.token = token.trim();
      }
      // Les credentials ne sont plus nécessaires pour le mode natif (Playwright utilise le profil Chrome)

      const endpoint = !isNative 
        ? `${API_URL}/api/v2/moodle/sync` 
        : `${API_URL}/api/v2/moodle/sync/native`;
      
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: isNative ? undefined : JSON.stringify(body),
      });

      if (res.ok) {
        onSyncStarted();
        onClose();
      } else {
        const data = await res.json();
        setError(data.detail || data.message || "Erreur de synchronisation");
      }
    } catch (err) {
      setError("Impossible de contacter le serveur.");
    } finally {
      setLoading(false);
    }
  };

  const handleTokenChange = (val: string) => {
    setCaptureSuccess(false);
    if (val.includes("token=")) {
      const match = val.match(/token=([a-zA-Z0-9+/=_-]+)/);
      if (match && match[1]) {
        setToken(match[1]);
        return;
      }
    }
    setToken(val);
  };

  const handleCapture = async () => {
    if (!url) {
      setError("Veuillez d'abord entrer l'URL Moodle.");
      return;
    }
    setCapturing(true);
    setError("");
    setCaptureSuccess(false);

    try {
      const res = await fetch(`${API_URL}/api/v2/moodle/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      const data = await res.json();

      if (res.ok && data.token) {
        setToken(data.token);
        setCaptureSuccess(true);
      } else {
        setError(data.detail || "Capture échouée ou annulée.");
      }
    } catch (err) {
      setError("Impossible de contacter le serveur.");
    } finally {
      setCapturing(false);
    }
  };

  return (
    <div className="nf-modal-overlay" onClick={onClose}>
      <div className="nf-modal nf-animate-in" onClick={(e) => e.stopPropagation()}>
        <div className="nf-modal-header">
          <h2 className="nf-modal-title">Synchronisation Moodle Docs</h2>
          <button className="nf-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSync} className="nf-modal-body">
          <p className="nf-modal-description">
            Synchronisez vos documents PDF depuis Moodle. Utilisez le mode <b>Jeton</b> si votre université utilise Microsoft SSO.
          </p>
          <p className="nf-modal-description" style={{ marginTop: "-4px", fontSize: "12px", color: "var(--nf-text-muted)" }}>
            Pour afficher des echéances dans le calendrier, ajoutez un lien d'export Moodle iCal/RSS (calendar/export) dans Parametres &gt; Connexions.
          </p>

          <div style={{ display: "flex", gap: "8px", background: "var(--nf-bg-secondary)", padding: "4px", borderRadius: "10px", marginBottom: "8px" }}>
            <button
              type="button"
              className={`nf-button nf-button--sm ${authMode === "credentials" ? "nf-button--primary" : "nf-button--ghost"}`}
              onClick={() => setAuthMode("credentials")}
              style={{ flex: 1 }}
            >
              Mode Natif (Recommandé)
            </button>
            <button
              type="button"
              className={`nf-button nf-button--sm ${authMode === "token" ? "nf-button--primary" : "nf-button--ghost"}`}
              onClick={() => setAuthMode("token")}
              style={{ flex: 1 }}
            >
              Manuellement
            </button>
          </div>

          <div className="nf-form-group">
            <label className="nf-label"><Globe size={14} /> URL Moodle</label>
            <input
              type="url"
              className="nf-input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://moodle.example.ca"
            />
          </div>

          {authMode === "credentials" ? (
            <div className="nf-animate-in">
              <p style={{ fontSize: "13px", color: "var(--nf-text-secondary)", marginBottom: "12px" }}>
                Le mode natif utilise votre session Chrome actuelle pour explorer les cours et devoirs.
              </p>
              
              <div className="nf-form-group">
                <label className="nf-label"><Globe size={14} /> URL Moodle</label>
                <input
                  type="url"
                  className="nf-input"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://moodle.usherbrooke.ca"
                />
                {isCalendarFeedUrl(url) && (
                  <p style={{ fontSize: "11px", color: "var(--nf-warning)", marginTop: "4px" }}>
                    ⚠️ Ceci semble être un lien de calendrier. NovaFlow extraira automatiquement la racine (https://moodle.usherbrooke.ca) pour la synchro des fichiers.
                  </p>
                )}
              </div>

              <div style={{ padding: "12px", background: "var(--nf-accent-glow)", borderRadius: "var(--nf-radius-sm)", border: "1px solid var(--nf-accent-dim)", marginTop: "8px" }}>
                 <p style={{ fontSize: "12px", color: "var(--nf-accent)", fontWeight: 600, margin: 0 }}>
                    ✨ Synchro Intelligente : NovaFlow détectera automatiquement vos cours et téléchargera les ressources.
                 </p>
              </div>
            </div>
          ) : (
            <div className="nf-form-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label className="nf-label"><Lock size={14} /> Jeton de service web</label>
                <button
                  type="button"
                  className="nf-button nf-button--sm nf-button--ghost"
                  onClick={async () => {
                    setCapturing(true);
                    try {
                      const res = await fetch(`${API_URL}/api/v2/moodle/login`, { method: "POST" });
                      if (res.ok) {
                        const data = await res.json();
                        if (data.success) {
                          setCaptureSuccess(true);
                        }
                      }
                    } catch (e) {} finally { setCapturing(false); }
                  }}
                  disabled={capturing}
                  style={{ fontSize: "11px", gap: "4px", display: "flex", alignItems: "center" }}
                >
                  {capturing ? (
                    <><RefreshCw size={12} className="nf-spin" /> Connexion...</>
                  ) : (
                    <><Globe size={12} /> Ouvrir Navigateur</>
                  )}
                </button>
              </div>
              <input
                type="text"
                className="nf-input"
                value={token}
                onChange={(e) => handleTokenChange(e.target.value)}
                required={authMode === "token" && !captureSuccess}
                placeholder="Le jeton sera détecté après connexion"
                style={captureSuccess ? { borderColor: "var(--nf-success, #22c55e)" } : undefined}
              />
              {captureSuccess && (
                <p style={{ fontSize: "11px", color: "var(--nf-success, #22c55e)", marginTop: "4px" }}>
                  ✓ Session détectée et active.
                </p>
              )}
              {capturing && (
                <p style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginTop: "4px" }}>
                  Une fenêtre Chrome s'est ouverte — connectez-vous. Elle se fermera une fois sur le dashboard.
                </p>
              )}
            </div>
          )}

          {error && <div className="nf-error-message">{error}</div>}

          <div className="nf-modal-footer">
            <button type="button" className="nf-button nf-button--ghost" onClick={onClose}>Annuler</button>
            <button type="submit" className="nf-button nf-button--primary" disabled={loading || capturing}>
              {loading ? <RefreshCw size={16} className="nf-spin" /> : "Lancer la synchro"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
