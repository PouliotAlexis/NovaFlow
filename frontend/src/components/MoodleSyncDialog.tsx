"use client";

import React, { useState, useEffect } from "react";
import { X, Lock, Globe, User, RefreshCw, Key } from "lucide-react";
import { api } from "@/services/api";

interface MoodleSyncDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncStarted: () => void;
}

export default function MoodleSyncDialog({ isOpen, onClose, onSyncStarted }: MoodleSyncDialogProps) {
  const [authMode, setAuthMode] = useState<"sso" | "credentials">("sso");
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const checkStatus = async () => {
        try {
          const res = await api.get("/api/v2/moodle/session/status");
          const data = await res.json();
          if (!data.has_token) {
             const local = localStorage.getItem("moodle_session");
             if (local) {
               const localData = JSON.parse(local);
               setIsConnected(!!localData.token);
               return;
             }
          }
          setIsConnected(data.has_token);
        } catch (err) {
          const local = localStorage.getItem("moodle_session");
          if (local) {
             const localData = JSON.parse(local);
             setIsConnected(!!localData.token);
          } else {
             setIsConnected(false);
          }
        }
      };
      checkStatus();
    }
  }, [isOpen]);
  const [error, setError] = useState("");


  // Pré-remplir avec l'URL Moodle depuis les settings (normalisée automatiquement)
  useEffect(() => {
    if (!isOpen) return;
    api.get("/api/settings/moodle")
      .then((r) => r.json())
      .then((data) => {
        const first = data.urls?.[0] || data.url || "";
        if (first) {
          try {
            const parsed = new URL(first);
            setUrl(`${parsed.protocol}//${parsed.hostname}${parsed.port ? ':' + parsed.port : ''}`);
          } catch {
            setUrl(first);
          }
        }
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSync = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Normaliser l'URL
      let normalizedUrl = url.trim();
      try {
        const parsed = new URL(normalizedUrl);
        normalizedUrl = `${parsed.protocol}//${parsed.hostname}${parsed.port ? ':' + parsed.port : ''}`;
      } catch {
        // URL invalide, on laisse tel quel
      }

      if (authMode === "sso") {
        // Mode SSO : utilise le token capturé via le bouton "Connecter" du dashboard ou localStorage
        const localSession = localStorage.getItem("moodle_session");
        const token = localSession ? JSON.parse(localSession).token : null;
        
        const body = { url: normalizedUrl, token: token };
        
        const res = await api.post("/api/v2/moodle/sync", body);
        if (res.ok) {
          onSyncStarted();
          onClose();
        } else {
          const data = await res.json();
          setError(data.detail || data.message || "Erreur de synchronisation. As-tu cliqué sur 'Connecter' d'abord ?");
        }
      } else {
        // Mode identifiants : username/password via l'API Moodle
        if (!username || !password) {
          setError("Veuillez entrer votre CIP et mot de passe.");
          setLoading(false);
          return;
        }
        const body = { url: normalizedUrl, username, password };
        const res = await api.post("/api/v2/moodle/sync", body);
        if (res.ok) {
          onSyncStarted();
          onClose();
        } else {
          const data = await res.json();
          setError(data.detail || data.message || "Erreur de synchronisation");
        }
      }
    } catch (err) {
      setError("Impossible de contacter le serveur.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nf-modal-overlay" onClick={onClose}>
      <div className="nf-modal nf-animate-in" onClick={(e) => e.stopPropagation()}>
        <div className="nf-modal-header">
          <h2 className="nf-modal-title">Synchronisation Moodle</h2>
          <button className="nf-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSync} className="nf-modal-body">
          <p className="nf-modal-description">
            Synchronisez vos documents depuis Moodle. L'URL sera normalisée automatiquement.
          </p>

          {/* Onglets */}
          <div style={{ display: "flex", gap: "6px", background: "var(--nf-bg-secondary)", padding: "5px", borderRadius: "12px", marginBottom: "12px" }}>
            <button
              type="button"
              onClick={() => setAuthMode("sso")}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "10px 16px",
                borderRadius: "9px",
                border: "none",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: 600,
                transition: "all 0.2s ease",
                background: authMode === "sso" ? "var(--nf-accent)" : "transparent",
                color: authMode === "sso" ? "#fff" : "var(--nf-text-muted)",
                boxShadow: authMode === "sso" ? "0 2px 8px rgba(99, 102, 241, 0.35)" : "none",
              }}
            >
              <Key size={15} /> Connexion SSO
            </button>
            <button
              type="button"
              onClick={() => setAuthMode("credentials")}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "10px 16px",
                borderRadius: "9px",
                border: "none",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: 600,
                transition: "all 0.2s ease",
                background: authMode === "credentials" ? "var(--nf-accent)" : "transparent",
                color: authMode === "credentials" ? "#fff" : "var(--nf-text-muted)",
                boxShadow: authMode === "credentials" ? "0 2px 8px rgba(99, 102, 241, 0.35)" : "none",
              }}
            >
              <User size={15} /> Identifiants
            </button>
          </div>

          {/* URL Moodle (commun) */}
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

          {/* Mode SSO */}
          {authMode === "sso" ? (
            <div className="nf-animate-in">
              <div style={{ padding: "12px", background: "var(--nf-accent-glow)", borderRadius: "var(--nf-radius-sm)", border: "1px solid var(--nf-accent-dim)" }}>
                <p style={{ fontSize: "12px", color: "var(--nf-accent)", fontWeight: 600, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                  ✨ {isConnected ? "Session Connectée !" : "Capture de session SSO"}
                  {isConnected && <span style={{ padding: "2px 6px", background: "#22c55e", color: "white", borderRadius: "4px", fontSize: "10px" }}>OK</span>}
                </p>
                
                {!isConnected && (
                  <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid var(--nf-accent-dim)" }}>
                    <label className="nf-label" style={{ fontSize: "11px" }}>
                      Ou colle ici le lien `moodlemobile://` (si tu n'as pas l'extension) :
                    </label>
                    <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                      <input 
                        type="text" 
                        className="nf-input" 
                        style={{ fontSize: "11px", height: "32px" }}
                        placeholder="moodlemobile://token=..."
                        onChange={async (e) => {
                          const val = e.target.value;
                          if (val.includes("token=")) {
                            const token = val.split("token=")[1].split("&")[0];
                            setLoading(true);
                            try {
                              const res = await api.post("/api/v2/moodle/sync", { url, token });
                              if (res.ok) {
                                onSyncStarted();
                                onClose();
                              }
                            } catch (err) {}
                            setLoading(false);
                          }
                        }}
                      />
                    </div>
                  </div>
                )}
                
                {isConnected && (
                  <p style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginTop: "8px" }}>
                    Ta session est déjà active. Clique sur "Lancer la synchronisation" ci-dessous.
                  </p>
                )}
              </div>
            </div>
          ) : (
            /* Mode Identifiants */
            <div className="nf-animate-in">
              <p style={{ fontSize: "12px", color: "var(--nf-text-muted)", marginBottom: "8px" }}>
                ⚠️ Ne fonctionne que si votre Moodle accepte la connexion par identifiants directs (pas Microsoft SSO).
              </p>
              <div className="nf-form-group">
                <label className="nf-label"><User size={14} /> CIP / Nom d'utilisateur</label>
                <input
                  type="text"
                  className="nf-input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="votre_cip"
                />
              </div>
              <div className="nf-form-group">
                <label className="nf-label"><Lock size={14} /> Mot de passe</label>
                <input
                  type="password"
                  className="nf-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </div>
          )}

          {error && <div className="nf-error-message">{error}</div>}

          <div className="nf-modal-footer">
            <button type="button" className="nf-button nf-button--ghost" onClick={onClose}>Annuler</button>
            <button type="submit" className="nf-button nf-button--primary" disabled={loading}>
              {loading ? <RefreshCw size={16} className="nf-spin" /> : "Lancer la synchro"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
