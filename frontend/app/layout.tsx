import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "ONZ Projet — Assistant de Montage de Projets",
  description:
    "Générez automatiquement des documents professionnels pour vos projets de développement international.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-creme">
        <Navbar />
        <main className="min-h-[calc(100vh-64px)]">{children}</main>
        <footer className="bg-bleu-marine text-white text-center py-4 text-sm font-source">
          © {new Date().getFullYear()} ONZ Projet — Tous droits réservés
        </footer>
      </body>
    </html>
  );
}
