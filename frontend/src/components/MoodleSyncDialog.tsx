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
      const body: any = { url };
      if (authMode === "token") {
        body.token = token.trim();
      } else {
        body.username = username.trim();
        body.password = password;
      }

      const res = await fetch(`${API_URL}/api/v2/moodle/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const cleanUrl = url.trim();
        if (isCalendarFeedUrl(cleanUrl)) {
          await fetch(`${API_URL}/api/settings/moodle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: cleanUrl }),
          });
          window.dispatchEvent(new CustomEvent("novaflow-account-changed"));
        }
        onSyncStarted();
        onClose();
      } else {
        const data = await res.json();
        setError(data.detail || "Erreur de synchronisation");
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
              Identifiants
            </button>
            <button
              type="button"
              className={`nf-button nf-button--sm ${authMode === "token" ? "nf-button--primary" : "nf-button--ghost"}`}
              onClick={() => setAuthMode("token")}
              style={{ flex: 1 }}
            >
              Jeton (SSO Ready)
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
            <>
              <div className="nf-form-group">
                <label className="nf-label"><User size={14} /> Identifiant (CIP)</label>
                <input
                  type="text"
                  className="nf-input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="pous1234"
                />
              </div>

              <div className="nf-form-group">
                <label className="nf-label"><Lock size={14} /> Mot de passe</label>
                <input
                  type="password"
                  className="nf-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </>
          ) : (
            <div className="nf-form-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label className="nf-label"><Lock size={14} /> Jeton de service web</label>
                <button
                  type="button"
                  className="nf-button nf-button--sm nf-button--ghost"
                  onClick={handleCapture}
                  disabled={capturing}
                  style={{ fontSize: "11px", gap: "4px", display: "flex", alignItems: "center" }}
                >
                  {capturing ? (
                    <><RefreshCw size={12} className="nf-spin" /> Connexion en cours...</>
                  ) : (
                    <><Cpu size={12} /> Capturer via navigateur</>
                  )}
                </button>
              </div>
              <input
                type="text"
                className="nf-input"
                value={token}
                onChange={(e) => handleTokenChange(e.target.value)}
                required
                placeholder="Cliquez sur 'Capturer' ou collez le jeton ici"
                style={captureSuccess ? { borderColor: "var(--nf-success, #22c55e)" } : undefined}
              />
              {captureSuccess && (
                <p style={{ fontSize: "11px", color: "var(--nf-success, #22c55e)", marginTop: "4px" }}>
                  ✓ Token capturé automatiquement.
                </p>
              )}
              {capturing && (
                <p style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginTop: "4px" }}>
                  Un navigateur Chromium s'est ouvert — connectez-vous avec Microsoft SSO. Il se fermera automatiquement.
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
