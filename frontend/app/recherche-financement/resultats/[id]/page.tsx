"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getRechercheFinancement, RechercheFinancementResponse, UnauthorizedError } from "@/lib/api";
import { FINANCEMENT_CATEGORIE_ORDER, FINANCEMENT_CATEGORIES } from "@/lib/constants";
import AuthGuard from "@/components/AuthGuard";
import OpportuniteCard from "@/components/OpportuniteCard";

function ResultatsContent({ rechercheId }: { rechercheId: number }) {
  const [recherche, setRecherche] = useState<RechercheFinancementResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRechercheFinancement(rechercheId)
      .then(setRecherche)
      .catch((err) => {
        if (err instanceof UnauthorizedError) return;
        setError(err instanceof Error ? err.message : "Résultats introuvables.");
      })
      .finally(() => setLoading(false));
  }, [rechercheId]);

  if (loading) {
    return (
      <div className="flex justify-center py-32">
        <div className="w-10 h-10 rounded-full border-4 border-gray-200 border-t-bleu-marine animate-spin" />
      </div>
    );
  }

  if (error || !recherche) {
    return (
      <div className="card max-w-lg mx-auto mt-10 text-center py-12 border-red-200">
        <p className="text-red-500 font-source font-semibold">{error || "Résultats introuvables."}</p>
      </div>
    );
  }

  const { resultats } = recherche;
  const byCategorie = FINANCEMENT_CATEGORIE_ORDER.map((cle) => ({
    cle,
    meta: FINANCEMENT_CATEGORIES[cle],
    opportunites: resultats.opportunites.filter((o) => o.categorie === cle),
  })).filter((g) => g.opportunites.length > 0);

  return (
    <div className="py-12 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link href={`/recherche-financement/${recherche.project_id}`} className="font-source text-sm text-vert-sauge hover:underline">
            ← Retour au projet
          </Link>
          <h1 className="font-playfair text-3xl font-bold text-bleu-marine mt-2">
            Financements pour « {recherche.project_nom} »
          </h1>
          <p className="font-source text-gray-600 mt-2">{resultats.resume}</p>
          <div className="mt-3">
            {recherche.recherche_live ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-vert-sauge/10 text-vert-sauge border border-vert-sauge/30 px-3 py-1 text-xs font-semibold font-source">
                🌐 Recherche en direct sur Internet
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 text-orange-700 border border-orange-200 px-3 py-1 text-xs font-semibold font-source">
                ⚠ Estimation basée sur les connaissances du modèle — à vérifier auprès des bailleurs
              </span>
            )}
          </div>
        </div>

        {resultats.opportunites.length === 0 && (
          <div className="card text-center py-16">
            <p className="font-playfair text-xl text-bleu-marine">
              Aucune opportunité identifiée pour le moment
            </p>
            <p className="font-source text-gray-500 mt-2">
              Relancez une recherche ultérieurement — de nouveaux appels à projets s&apos;ouvrent régulièrement.
            </p>
          </div>
        )}

        <div className="flex flex-col gap-8">
          {byCategorie.map((g) => (
            <section key={g.cle}>
              <h2 className="font-source text-sm font-bold uppercase tracking-wide text-gray-500 mb-3">
                {g.meta.icon} {g.meta.label} ({g.opportunites.length})
              </h2>
              <div className="flex flex-col gap-4">
                {g.opportunites.map((o, i) => (
                  <OpportuniteCard key={i} opportunite={o} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function RechercheFinancementResultatsPage({ params }: { params: { id: string } }) {
  const rechercheId = Number(params.id);
  return (
    <AuthGuard>
      <ResultatsContent rechercheId={rechercheId} />
    </AuthGuard>
  );
}
