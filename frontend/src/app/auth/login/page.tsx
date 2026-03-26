"use client";

import React, { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { LogIn, Mail, Lock, Sparkles } from "lucide-react";
import Link from "next/link";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          username: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        login(data.access_token, data.user);
      } else {
        setError(data.detail || "Identifiants invalides");
      }
    } catch (err) {
      setError("Erreur de connexion au serveur");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container nf-auth-bg">
      <div className="auth-card nf-glass nf-animate-in">
        <div className="auth-header">
          <div className="auth-logo">
            <div className="nf-logo-icon-wrapper">
              <Sparkles size={28} className="nf-logo-sparkle" />
            </div>
            <span className="nf-logo-text">NovaFlow</span>
          </div>
          <h1>Bon retour !</h1>
          <p>Connectez-vous pour accéder à votre univers.</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}
          
          <div className="auth-input-group">
            <label><Mail size={14} /> Email</label>
            <input
              type="email"
              placeholder="votre@email.com"
              className="nf-input-modern"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="auth-input-group">
            <label><Lock size={14} /> Mot de passe</label>
            <input
              type="password"
              placeholder="••••••••"
              className="nf-input-modern"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button 
            type="submit" 
            className="nf-button nf-button--primary nf-shimmer" 
            disabled={isLoading}
          >
            {isLoading ? "Connexion..." : <><LogIn size={18} /> Se connecter</>}
          </button>
        </form>

        <div className="auth-footer">
          <p>Pas encore de compte ? <Link href="/auth/register">Créez-en un ici</Link></p>
        </div>
      </div>

      <style jsx>{`
        .auth-container {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          padding: 20px;
        }
        .auth-card {
          width: 100%;
          max-width: 420px;
          padding: 48px 40px;
          border-radius: 28px;
          position: relative;
          z-index: 1;
        }
        .auth-header {
          text-align: center;
          margin-bottom: 36px;
        }
        .auth-logo {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-bottom: 28px;
        }
        .nf-logo-icon-wrapper {
          width: 44px;
          height: 44px;
          background: var(--nf-accent-gradient);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 15px rgba(124, 92, 252, 0.3);
        }
        .nf-logo-sparkle {
          color: white;
        }
        .nf-logo-text {
          font-size: 26px;
          font-weight: 800;
          letter-spacing: -0.5px;
          background: var(--nf-accent-gradient);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        h1 {
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 8px;
          color: var(--nf-text);
        }
        p {
          color: var(--nf-text-secondary);
          font-size: 14px;
        }
        .auth-form {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .auth-input-group {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .auth-input-group label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          font-weight: 600;
          color: var(--nf-text-secondary);
          padding-left: 4px;
        }
        .auth-error {
          padding: 12px 16px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.2);
          color: var(--nf-danger);
          font-size: 13px;
          border-radius: 10px;
          text-align: center;
        }
        .auth-footer {
          margin-top: 36px;
          text-align: center;
          font-size: 14px;
          color: var(--nf-text-secondary);
        }
        .auth-footer a {
          color: var(--nf-accent);
          text-decoration: none;
          font-weight: 600;
          transition: color 0.2s;
        }
        .auth-footer a:hover {
          color: var(--nf-accent-secondary);
          text-underline-offset: 4px;
          text-decoration: underline;
        }
        .nf-button {
          margin-top: 8px;
          height: 48px;
          font-size: 15px;
          font-weight: 700;
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          cursor: pointer;
          transition: all 0.2s;
          border: none;
        }
        .nf-button--primary {
          background: var(--nf-accent-gradient);
          color: white;
          box-shadow: 0 4px 20px rgba(124, 92, 252, 0.2);
        }
        .nf-button--primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 25px rgba(124, 92, 252, 0.3);
        }
        .nf-button--primary:active {
          transform: translateY(0);
        }
        .nf-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
          transform: none;
        }
      `}</style>
    </div>
  );
}
