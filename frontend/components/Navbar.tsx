"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Accueil" },
  { href: "/nouveau-projet", label: "Nouveau projet" },
  { href: "/mes-projets", label: "Mes projets" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="bg-bleu-marine text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 font-playfair font-bold text-xl">
          <span className="text-vert-sauge">ONZ</span>
          <span>Projet</span>
        </Link>
        <div className="flex items-center gap-6">
          {links.map((l) => (
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
        </div>
      </div>
    </nav>
  );
}
