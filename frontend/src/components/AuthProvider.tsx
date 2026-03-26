"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
  id: string;
  email: string;
  full_name?: string;
  ai_mode?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Restaurer la session depuis le localStorage
    const savedToken = localStorage.getItem("nf_token");
    const savedUser = localStorage.getItem("nf_user");

    if (savedToken && savedUser && savedUser !== "undefined") {
      try {
        setToken(savedToken);
        const parsedUser = JSON.parse(savedUser);
        if (parsedUser) {
          setUser(parsedUser);
        } else {
           throw new Error("Parsed user is null");
        }
      } catch (e) {
        console.error("Failed to parse saved user", e);
        localStorage.removeItem("nf_token");
        localStorage.removeItem("nf_user");
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    // Redirection automatique si non authentifié
    if (!isLoading && !token && !pathname.startsWith("/auth")) {
      router.push("/auth/login");
    }
  }, [token, isLoading, pathname, router]);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("nf_token", newToken);
    localStorage.setItem("nf_user", JSON.stringify(newUser));
    router.push("/");
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("nf_token");
    localStorage.removeItem("nf_user");
    router.push("/auth/login");
  };

  const refreshUser = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const newUser = await res.json();
        setUser(newUser);
        localStorage.setItem("nf_user", JSON.stringify(newUser));
      }
    } catch (e) {
      console.error("Failed to refresh user", e);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
