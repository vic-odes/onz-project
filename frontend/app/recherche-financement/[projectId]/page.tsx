"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  getProject,
  listRecherchesPourProjet,
  rechercherFinancement,
  ProjectSummary,
  RechercheFinancementSummary,
  UnauthorizedError,
} from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import FinancementLoader from "@/components/FinancementLoader";

function LauncherContent({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [historique, setHistorique] = useState<RechercheFinancementSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getProject(projectId), listRecherchesPourProjet(projectId)])
      .then(([p, h]) => {
        setProject(p);
        setHistorique(h);
      })
      .catch((err) => {
        if (err instanceof UnauthorizedError) return;
        setLoadError(err instanceof Error ? err.message : "Projet introuvable.");
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleSearch = async () => {
    setSearching(true);
    setSearchError(null);
    try {
      const recherche = await rechercherFinancement(projectId);
      router.push(`/recherche-financement/resultats/${recherche.id}`);
    } catch (e: unknown) {
      setSearchError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setSearching(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-32">
        <div className="w-10 h-10 rounded-full border-4 border-gray-200 border-t-bleu-marine animate-spin" />
      </div>
    );
  }

  if (loadError || !project) {
    return (
      <div className="card max-w-lg mx-auto mt-10 text-center py-12 border-red-200">
        <p className="text-red-500 font-source font-semibold">{loadError || "Projet introuvable."}</p>
      </div>
    );
  }

  if (searching) {
    return (
      <div className="card max-w-2xl mx-auto mt-10">
        <FinancementLoader error={searchError} />
      </div>
    );
  }

  return (
    <div className="py-12 px-6">
      <div className="max-w-2xl mx-auto">
        <div className="card text-center py-10">
          <p className="font-source text-sm text-vert-sauge font-semibold uppercase tracking-wide mb-2">
            Recherche de financement
          </p>
          <h1 className="font-playfair text-2xl font-bold text-bleu-marine mb-2">{project.nom}</h1>
          <p className="font-source text-gray-500 mb-6">
            🌍 {project.pays} · {project.secteur}
            {project.budget_total != null && ` · 💰 ${project.budget_total.toLocaleString("fr-FR")} USD`}
          </p>
          {searchError && (
            <p role="alert" className="font-source text-sm text-red-600 mb-3">{searchError}</p>
          )}
          <button type="button" onClick={handleSearch} className="btn-accent text-lg px-8">
            🔎 Rechercher les financements disponibles
          </button>
        </div>

        {historique.length > 0 && (
          <div className="mt-8">
            <p className="font-source text-sm font-semibold text-gray-500 mb-3">
              Recherches précédentes pour ce projet
            </p>
            <div className="flex flex-col gap-2">
              {historique.map((h) => (
                <Link
                  key={h.id}
                  href={`/recherche-financement/resultats/${h.id}`}
                  className="card flex items-center justify-between gap-4 py-3 hover:shadow-lg transition-shadow"
                >
                  <div>
                    <p className="font-source text-sm text-gray-700">{h.resume || "Résultats de recherche"}</p>
                    <p className="font-source text-xs text-gray-400">
                      {new Date(h.created_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" })}
                      {" · "}{h.nb_opportunites} opportunité(s)
                    </p>
                  </div>
                  <span className="font-source text-sm font-semibold text-bleu-marine shrink-0">Voir →</span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RechercheFinancementLauncherPage({ params }: { params: { projectId: string } }) {
  const projectId = Number(params.projectId);
  return (
    <AuthGuard>
      <LauncherContent projectId={projectId} />
    </AuthGuard>
  );
}
