"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  AuthUser,
  clearStoredAuth,
  getStoredToken,
  getStoredUser,
  setStoredAuth,
} from "@/lib/auth";
import {
  fetchMe,
  login as apiLogin,
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

  // Au montage : si un token + user existent en localStorage, les rétablir et
  // valider le token via /me en arrière-plan. Si invalide, on déconnecte.
  useEffect(() => {
    const token = getStoredToken();
    const stored = getStoredUser();
    if (!token || !stored) {
      setLoading(false);
      return;
    }
    setUser(stored);
    fetchMe()
      .then((fresh) => {
        setUser(fresh);
        // rafraîchit les infos user en localStorage sans toucher au token
        setStoredAuth(token, fresh);
      })
      .catch((err) => {
        if (err instanceof UnauthorizedError) {
          // token expiré/invalide — déjà purgé par apiFetch
          setUser(null);
        }
        // autre erreur réseau : on garde le user en cache (mode optimiste)
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setStoredAuth(res.access_token, res.user);
    setUser(res.user);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const res = await apiRegister(email, password, fullName);
    setStoredAuth(res.access_token, res.user);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    clearStoredAuth();
    setUser(null);
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
