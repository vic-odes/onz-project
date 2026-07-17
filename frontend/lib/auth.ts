// Le JWT vit désormais dans un cookie httpOnly posé par le backend : il n'est
// JAMAIS accessible au JavaScript (immunité au vol de token par XSS).
// Seul le profil utilisateur (données non sensibles) est mis en cache local
// pour un affichage optimiste au rechargement de la page.

const USER_KEY = "onz_user";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setStoredUser(user: AuthUser): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredUser(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(USER_KEY);
}
