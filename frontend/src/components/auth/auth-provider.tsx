"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import api from "@/lib/api";

interface User {
  id: string;
  github_id: number;
  github_username: string;
  name: string;
  email: string | null;
  avatar_url: string | null;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = sessionStorage.getItem("access_token");
    if (token) {
      api.get("/api/auth/me")
        .then((res) => setUser(res.data))
        .catch(() => {
          sessionStorage.removeItem("access_token");
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = () => {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/github`;
  };

  const logout = async () => {
    await api.post("/api/auth/logout");
    sessionStorage.removeItem("access_token");
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuthContext must be used within AuthProvider");
  return context;
}
