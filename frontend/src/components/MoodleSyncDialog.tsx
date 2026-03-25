"use client";

import React, { useState, useEffect } from "react";
import { X, Lock, Globe, User, RefreshCw, Key } from "lucide-react";

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
  const [error, setError] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  // Pré-remplir avec l'URL Moodle depuis les settings (normalisée automatiquement)
  useEffect(() => {
    if (!isOpen) return;
    fetch(`${API_URL}/api/settings/moodle`)
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
        // Mode SSO : utilise le token capturé via le bouton "Connecter" du dashboard
        const res = await fetch(`${API_URL}/api/v2/moodle/sync/native`, {
          method: "POST",
        });
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
        const res = await fetch(`${API_URL}/api/v2/moodle/sync`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
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
                <p style={{ fontSize: "12px", color: "var(--nf-accent)", fontWeight: 600, margin: 0 }}>
                  ✨ Utilise le bouton "Connecter" sur le dashboard pour capturer ta session Microsoft SSO, puis lance la synchro ici.
                </p>
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
