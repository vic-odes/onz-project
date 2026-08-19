"use client";
import { useEffect, useState } from "react";

// Même principe que GenerationLoader : le backend ne streame pas de progression
// pour cet appel (recherche + scoring en un seul aller-retour), on simule une
// progression douce pour rassurer l'utilisateur pendant les 10-30 secondes d'attente.
const STEP_LABELS = [
  "Analyse du profil du projet…",
  "Recherche des bailleurs compatibles…",
  "Vérification des appels ouverts…",
  "Calcul des scores de compatibilité…",
  "Finalisation des résultats…",
];

interface FinancementLoaderProps {
  done?: boolean;
  error?: string | null;
}

export default function FinancementLoader({ done, error }: FinancementLoaderProps) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (done || error) return;
    const interval = setInterval(() => setTick((t) => t + 1), 1500);
    return () => clearInterval(interval);
  }, [done, error]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center text-3xl">✗</div>
        <p className="font-playfair text-xl font-bold text-red-600">Erreur de recherche</p>
        <p role="alert" className="font-source text-gray-600 text-center max-w-md">{error}</p>
      </div>
    );
  }

  const label = STEP_LABELS[Math.min(tick, STEP_LABELS.length - 1)];
  const percent = ((Math.min(tick, STEP_LABELS.length - 1) + 1) / STEP_LABELS.length) * 100;

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-8">
      <div className="relative w-20 h-20" role="status" aria-label="Recherche de financements en cours">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
        <div className="absolute inset-0 rounded-full border-4 border-t-bleu-marine border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        <div className="absolute inset-2 rounded-full border-4 border-t-vert-sauge border-r-transparent border-b-transparent border-l-transparent animate-spin [animation-direction:reverse] [animation-duration:1.5s]" />
      </div>

      <div className="text-center">
        <p className="font-playfair text-xl font-bold text-bleu-marine mb-2">
          🔎 Recherche des opportunités de financement
        </p>
        <p className="font-source text-vert-sauge font-semibold min-h-[1.5rem] transition-all duration-500">
          {label}
        </p>
      </div>

      <div
        className="w-64 bg-gray-200 rounded-full h-2"
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="bg-vert-sauge h-2 rounded-full transition-all duration-500"
          style={{ width: `${Math.round(percent)}%` }}
        />
      </div>
      <p className="font-source text-xs text-gray-400">Cette opération peut prendre 10 à 30 secondes…</p>
    </div>
  );
}
