"use client";
import { OpportuniteFinancement } from "@/lib/api";
import { FIABILITE_LABELS, FINANCEMENT_CATEGORIES } from "@/lib/constants";

function formatMontant(opp: OpportuniteFinancement): string | null {
  const { montant_min, montant_max, devise } = opp;
  if (montant_min == null && montant_max == null) return null;
  const fmt = (n: number) => n.toLocaleString("fr-FR");
  if (montant_min != null && montant_max != null && montant_min !== montant_max) {
    return `${fmt(montant_min)} – ${fmt(montant_max)} ${devise}`.trim();
  }
  return `${fmt(montant_max ?? montant_min ?? 0)} ${devise}`.trim();
}

export default function OpportuniteCard({ opportunite }: { opportunite: OpportuniteFinancement }) {
  const cat = FINANCEMENT_CATEGORIES[opportunite.categorie] ?? FINANCEMENT_CATEGORIES.a_etudier;
  const montant = formatMontant(opportunite);
  const nonEligible = opportunite.categorie === "non_eligible";

  return (
    <article className="card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-playfair text-lg font-bold text-bleu-marine leading-snug">
            {opportunite.bailleur || "Bailleur non précisé"}
            {opportunite.programme && (
              <span className="font-source text-base font-normal text-gray-500"> — {opportunite.programme}</span>
            )}
          </h3>
          {opportunite.nom_appel && (
            <p className="font-source text-sm text-gray-500 mt-0.5">{opportunite.nom_appel}</p>
          )}
        </div>
        <span className={`shrink-0 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold font-source ${cat.badgeClass}`}>
          {cat.icon} {nonEligible ? cat.label : `${cat.label} · ${opportunite.score_compatibilite}%`}
        </span>
      </div>

      {opportunite.description && (
        <p className="font-source text-sm text-gray-600">{opportunite.description}</p>
      )}

      <div className="flex flex-wrap gap-2 font-source text-xs">
        {montant && (
          <span className="inline-flex items-center gap-1 rounded-full border border-vert-sauge/20 bg-vert-sauge/10 px-2.5 py-1 font-semibold text-vert-sauge">
            💰 {montant}
          </span>
        )}
        {opportunite.taux_cofinancement_max && (
          <span className="inline-flex items-center gap-1 rounded-full border border-gray-100 bg-gray-50 px-2.5 py-1 text-gray-600">
            % {opportunite.taux_cofinancement_max}
          </span>
        )}
        <span className="inline-flex items-center gap-1 rounded-full border border-gray-100 bg-gray-50 px-2.5 py-1 text-gray-600">
          📅 {opportunite.depot_permanent
            ? "Dépôt permanent"
            : opportunite.date_limite || "Date limite non disponible – à vérifier auprès du bailleur"}
        </span>
      </div>

      {(opportunite.raisons_compatibilite.length > 0 || opportunite.points_vigilance.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-source text-sm">
          {opportunite.raisons_compatibilite.length > 0 && (
            <ul className="space-y-1">
              {opportunite.raisons_compatibilite.map((r, i) => (
                <li key={i} className="text-green-700 flex gap-1.5"><span>✓</span><span>{r}</span></li>
              ))}
            </ul>
          )}
          {opportunite.points_vigilance.length > 0 && (
            <ul className="space-y-1">
              {opportunite.points_vigilance.map((p, i) => (
                <li key={i} className="text-orange-600 flex gap-1.5"><span>⚠</span><span>{p}</span></li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-3 flex-wrap">
        <div className="font-source text-xs text-gray-400">
          {FIABILITE_LABELS[opportunite.fiabilite] ?? ""}
          {opportunite.date_verification && ` · Vérifié le ${opportunite.date_verification}`}
        </div>
        <div className="flex items-center gap-2">
          {opportunite.source_officielle && (
            <a
              href={opportunite.source_officielle}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg border border-bleu-marine px-3 py-1.5 text-sm font-semibold text-bleu-marine
                         transition-colors hover:bg-bleu-marine hover:text-white font-source"
            >
              Source officielle
            </a>
          )}
          {opportunite.lien_candidature && (
            <a
              href={opportunite.lien_candidature}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg border border-vert-sauge px-3 py-1.5 text-sm font-semibold text-vert-sauge
                         transition-colors hover:bg-vert-sauge hover:text-white font-source"
            >
              Voir l&apos;appel
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
