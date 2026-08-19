"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { listProjects, ProjectSummary, UnauthorizedError } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import ImporterProjetPdf from "@/components/ImporterProjetPdf";

function RechercheFinancementContent() {
  const [mode, setMode] = useState<"existant" | "import">("existant");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((err) => {
        if (err instanceof UnauthorizedError) return;
        setError(err instanceof Error ? err.message : "Impossible de charger les projets.");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="py-12 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="font-playfair text-4xl font-bold text-bleu-marine">
            🔎 Rechercher un financement
          </h1>
          <p className="font-source text-gray-600 mt-1">
            Choisissez un projet déjà monté dans l&apos;application, ou importez le document d&apos;un
            projet monté ailleurs : nous recherchons automatiquement les bailleurs, lignes de
            financement et appels à projets actuellement compatibles.
          </p>
        </div>

        <div className="flex gap-2 mb-6 border-b border-gray-200">
          <button
            type="button"
            onClick={() => setMode("existant")}
            className={`px-4 py-2 font-source text-sm font-semibold border-b-2 transition-colors
              ${mode === "existant" ? "border-vert-sauge text-vert-sauge" : "border-transparent text-gray-500 hover:text-bleu-marine"}`}
          >
            Projet déjà monté dans l&apos;application
          </button>
          <button
            type="button"
            onClick={() => setMode("import")}
            className={`px-4 py-2 font-source text-sm font-semibold border-b-2 transition-colors
              ${mode === "import" ? "border-vert-sauge text-vert-sauge" : "border-transparent text-gray-500 hover:text-bleu-marine"}`}
          >
            Importer un document PDF
          </button>
        </div>

        {mode === "import" && <ImporterProjetPdf />}

        {mode === "existant" && loading && (
          <div className="flex justify-center py-20">
            <div className="w-10 h-10 rounded-full border-4 border-gray-200 border-t-bleu-marine animate-spin" />
          </div>
        )}

        {mode === "existant" && error && (
          <div className="card text-center py-12 border-red-200">
            <p className="text-red-500 font-source font-semibold">{error}</p>
          </div>
        )}

        {mode === "existant" && !loading && !error && projects.length === 0 && (
          <div className="card text-center py-16">
            <p className="font-playfair text-xl text-bleu-marine mb-4">
              Aucun projet monté pour l&apos;instant
            </p>
            <p className="font-source text-gray-500 mb-6">
              Créez un projet dans l&apos;application, ou importez le PDF d&apos;un projet déjà
              monté ailleurs via l&apos;onglet ci-dessus.
            </p>
            <Link href="/nouveau-projet" className="btn-accent">
              Créer un projet
            </Link>
          </div>
        )}

        {mode === "existant" && !loading && !error && projects.length > 0 && (
          <div className="flex flex-col gap-3">
            {projects.map((p) => (
              <Link
                key={p.id}
                href={`/recherche-financement/${p.id}`}
                className="card flex items-center justify-between gap-4 hover:shadow-lg transition-shadow"
              >
                <div>
                  <p className="font-playfair text-lg font-bold text-bleu-marine">{p.nom}</p>
                  <p className="font-source text-sm text-gray-500">
                    🌍 {p.pays} · {p.secteur}
                  </p>
                </div>
                <span className="btn-secondary shrink-0">Rechercher →</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function RechercheFinancementPage() {
  return (
    <AuthGuard>
      <RechercheFinancementContent />
    </AuthGuard>
  );
}
