"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";

const privateLinks = [
  { href: "/nouveau-projet", label: "Nouveau projet" },
  { href: "/mes-projets", label: "Mes projets" },
  { href: "/recherche-financement", label: "Rechercher un financement" },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Ferme le menu user au clic extérieur
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    router.push("/");
  };

  const visibleLinks = [{ href: "/", label: "Accueil" }, ...(user ? privateLinks : [])];

  const initials = user
    ? (user.full_name || user.email).slice(0, 2).toUpperCase()
    : "";

  return (
    <nav className="bg-bleu-marine text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 font-playfair font-bold text-xl">
          <span className="text-vert-sauge">ONZ</span>
          <span>Projet</span>
        </Link>

        <div className="flex items-center gap-6">
          {visibleLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`font-source text-sm font-semibold transition-colors duration-200
                ${pathname === l.href
                  ? "text-vert-sauge border-b-2 border-vert-sauge pb-0.5"
                  : "text-gray-300 hover:text-white"
                }`}
            >
              {l.label}
            </Link>
          ))}

          {/* Zone auth */}
          {loading ? (
            <span className="w-8 h-8 rounded-full border-2 border-gray-400 border-t-vert-sauge animate-spin" />
          ) : user ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-2 bg-bleu-marine border border-vert-sauge/40 rounded-full pl-1 pr-3 py-1 hover:border-vert-sauge transition-colors"
                aria-haspopup="true"
                aria-expanded={menuOpen ? "true" : "false"}
              >
                <span className="w-7 h-7 rounded-full bg-vert-sauge text-white flex items-center justify-center text-xs font-bold font-source">
                  {initials}
                </span>
                <span className="font-source text-sm max-w-[150px] truncate">
                  {user.full_name || user.email}
                </span>
                <span className="text-xs text-gray-300">▾</span>
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white text-bleu-marine rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="font-source text-xs text-gray-500">Connecté en tant que</p>
                    <p className="font-source text-sm font-semibold truncate">{user.email}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 font-source text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    Se déconnecter
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className={`font-source text-sm font-semibold transition-colors
                  ${pathname === "/login" ? "text-vert-sauge" : "text-gray-300 hover:text-white"}`}
              >
                Connexion
              </Link>
              <Link
                href="/register"
                className="bg-vert-sauge text-white px-3 py-1.5 rounded-lg font-source text-sm font-semibold hover:bg-opacity-90 transition-all"
              >
                S'inscrire
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
