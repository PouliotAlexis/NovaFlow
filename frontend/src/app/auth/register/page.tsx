"use client";

import React, { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { UserPlus, Mail, Lock, User, ArrowLeft, Rocket } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";

export default function RegisterPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      // 1. Inscription
      const regResponse = await api.post("/api/auth/register", {
          email: email,
          password: password,
          full_name: fullName,
      });

      const regData = await regResponse.json();

      if (!regResponse.ok) {
        setError(regData.detail || "Erreur lors de l'inscription");
        setIsLoading(false);
        return;
      }

      // 2. Connexion automatique après inscription
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
      const loginResponse = await fetch(`${apiBaseUrl}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          username: email,
          password: password,
        }),
      });

      const loginData = await loginResponse.json();

      if (loginResponse.ok) {
        login(loginData.access_token, loginData.user);
      } else {
        router.push("/auth/login?registered=true");
      }
    } catch (err: any) {
      setError("Erreur de connexion au serveur");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container nf-auth-bg">
      <div className="auth-card nf-glass nf-animate-in">
        <Link href="/auth/login" className="auth-back-link" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ArrowLeft size={16} />
          <span>Retour</span>
        </Link>
        <div className="auth-header">
          <div className="auth-logo">
            <div className="nf-logo-icon-wrapper">
              <Rocket size={28} className="nf-logo-rocket" />
            </div>
            <span className="nf-logo-text">NovaFlow</span>
          </div>
          <h1>Rejoignez-nous</h1>
          <p>Créez votre compte pour commencer l'aventure.</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}
          
          <div className="auth-input-group">
            <label><User size={14} /> Nom Complet</label>
            <input
              type="text"
              placeholder="Prénom Nom"
              className="nf-input-modern"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>

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
            {isLoading ? "Création..." : <><UserPlus size={18} /> Créer mon compte</>}
          </button>
        </form>

        <div className="auth-footer">
          <p>Déjà un compte ? <Link href="/auth/login">Connectez-vous</Link></p>
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
          max-width: 440px;
          padding: 48px 40px;
          border-radius: 28px;
          position: relative;
          z-index: 1;
        }
        .auth-header {
          text-align: center;
          margin-bottom: 32px;
          position: relative;
        }
        .auth-back-link {
          position: absolute;
          left: 20px;
          top: 20px;
          display: flex !important;
          flex-direction: row !important;
          align-items: center !important;
          gap: 8px !important;
          padding: 8px 12px;
          border-radius: 10px;
          font-size: 13px;
          font-weight: 500;
          color: var(--nf-text-secondary);
          text-decoration: none;
          transition: all 0.2s;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          z-index: 10;
          white-space: nowrap !important;
          width: auto !important;
        }
        .auth-back-link:hover {
          color: var(--nf-text);
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.1);
        }
        .auth-logo {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-bottom: 24px;
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
        .nf-logo-rocket {
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
          gap: 20px;
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
          margin-top: 32px;
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
        }
        .nf-button {
          margin-top: 12px;
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
