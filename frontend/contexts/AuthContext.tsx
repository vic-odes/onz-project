"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  AuthUser,
  clearStoredUser,
  getStoredUser,
  setStoredUser,
} from "@/lib/auth";
import {
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  UnauthorizedError,
} from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean; // true tant que la session initiale n'est pas résolue
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Au montage : afficher le user en cache (optimiste) puis valider la session
  // via /me — le cookie httpOnly est envoyé automatiquement. En cas de 401, on
  // déconnecte ; sur une simple erreur réseau, on garde le cache.
  useEffect(() => {
    const stored = getStoredUser();
    if (stored) setUser(stored);
    fetchMe()
      .then((fresh) => {
        setUser(fresh);
        setStoredUser(fresh);
      })
      .catch((err) => {
        if (err instanceof UnauthorizedError) {
          setUser(null);
          clearStoredUser();
        }
        // autre erreur réseau : on garde le user en cache (mode optimiste)
      })
      .finally(() => setLoading(false));
  }, []);

  // Un 401 survenu sur n'importe quelle requête (session expirée en cours d'usage)
  // émet "onz:unauthorized" → on réinitialise l'état pour que l'AuthGuard redirige.
  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      clearStoredUser();
    };
    window.addEventListener("onz:unauthorized", onUnauthorized);
    return () => window.removeEventListener("onz:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setStoredUser(res.user);
    setUser(res.user);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const res = await apiRegister(email, password, fullName);
    setStoredUser(res.user);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    // Réinitialisation immédiate de l'UI, puis suppression du cookie côté serveur.
    clearStoredUser();
    setUser(null);
    void apiLogout();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
