"use client";
import { useEffect, useState } from "react";
import type { StreamPhase, StreamProgressEvent } from "@/lib/api";

// Libellé par défaut quand l'orchestrateur n'a pas (encore) émis de phase.
const FALLBACK_LABEL = "Préparation de la génération…";

// Heuristique : pour la phase generation, un document complet fait ~12 000 caractères.
// On tronque à 95 % pour ne pas afficher 100 % avant que la phase suivante n'arrive.
const GEN_CHARS_TARGET = 12_000;

const PHASE_BAR_RANGE: Record<StreamPhase, [number, number]> = {
  generation: [0, 0.85],     // 0 % → 85 %
  docx: [0.85, 0.95],        // 85 % → 95 %
  persistance: [0.95, 1.0],  // 95 % → 100 %
};

interface GenerationLoaderProps {
  onDownload?: () => void;
  downloadBlob?: Blob | null;
  fileName?: string;
  error?: string | null;
  /** Dernier event de progression reçu via SSE. Optionnel : si absent, fallback animé. */
  progress?: StreamProgressEvent | null;
}

export default function GenerationLoader({
  onDownload,
  downloadBlob,
  fileName = "projet_ONZ.docx",
  error,
  progress,
}: GenerationLoaderProps) {
  // Tick local utilisé uniquement quand on n'a pas de stream (mode bloquant historique).
  const [fallbackTick, setFallbackTick] = useState(0);
  useEffect(() => {
    if (downloadBlob || error || progress) return;
    const interval = setInterval(() => setFallbackTick((t) => t + 1), 1500);
    return () => clearInterval(interval);
  }, [downloadBlob, error, progress]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center text-3xl">
          ✗
        </div>
        <p className="font-playfair text-xl font-bold text-red-600">Erreur de génération</p>
        <p className="font-source text-gray-600 text-center max-w-md">{error}</p>
      </div>
    );
  }

  if (downloadBlob) {
    const url = URL.createObjectURL(downloadBlob);
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-6">
        <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center text-4xl">
          ✓
        </div>
        <p className="font-playfair text-2xl font-bold text-vert-sauge">
          Document généré avec succès !
        </p>
        <p className="font-source text-gray-600">
          Votre document Word professionnel est prêt.
        </p>
        <a
          href={url}
          download={fileName}
          onClick={onDownload}
          className="btn-primary inline-flex items-center gap-2 text-lg px-8 py-4"
        >
          <span>⬇</span>
          Télécharger le document .docx
        </a>
      </div>
    );
  }

  const { label, percent, detail } = computeDisplay(progress, fallbackTick);

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-8">
      <div className="relative w-20 h-20" role="status" aria-label="Génération en cours">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
        <div className="absolute inset-0 rounded-full border-4 border-t-bleu-marine border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        <div className="absolute inset-2 rounded-full border-4 border-t-vert-sauge border-r-transparent border-b-transparent border-l-transparent animate-spin [animation-direction:reverse] [animation-duration:1.5s]" />
      </div>

      <div className="text-center">
        <p className="font-playfair text-xl font-bold text-bleu-marine mb-2">
          Génération en cours
        </p>
        <p className="font-source text-vert-sauge font-semibold min-h-[1.5rem] transition-all duration-500">
          {label}
        </p>
        {detail && (
          <p className="font-source text-xs text-gray-400 mt-1">{detail}</p>
        )}
      </div>

      <div
        className="w-64 bg-gray-200 rounded-full h-2"
        role="progressbar"
        aria-valuenow={Math.round(percent * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="bg-vert-sauge h-2 rounded-full transition-all duration-500"
          style={{ width: `${Math.round(percent * 100)}%` }}
        />
      </div>
      <p className="font-source text-xs text-gray-400">
        Cette opération peut prendre 30 à 60 secondes…
      </p>
    </div>
  );
}

function computeDisplay(
  progress: StreamProgressEvent | null | undefined,
  fallbackTick: number,
): { label: string; percent: number; detail: string | null } {
  if (!progress) {
    // Mode legacy : pas d'info de phase, on simule une progression douce
    const fallbackLabels = [
      "Analyse du contexte du projet…",
      "Génération du cadre logique…",
      "Construction de l'analyse des risques…",
      "Calcul du budget…",
      "Finalisation du document Word…",
    ];
    const idx = Math.min(fallbackTick, fallbackLabels.length - 1);
    return {
      label: fallbackLabels[idx] ?? FALLBACK_LABEL,
      percent: (idx + 1) / fallbackLabels.length,
      detail: null,
    };
  }

  const [start, end] = PHASE_BAR_RANGE[progress.phase] ?? [0, 1];
  let phaseFill = 0;
  let detail: string | null = null;

  if (progress.phase === "generation" && typeof progress.chars === "number") {
    phaseFill = Math.min(progress.chars / GEN_CHARS_TARGET, 1);
    detail = `${progress.chars.toLocaleString("fr-FR")} caractères reçus`;
  } else if (progress.type === "phase") {
    phaseFill = 0.5; // mid-phase
  } else {
    phaseFill = 1;
  }

  const label = progress.label ?? phaseDefaultLabel(progress.phase);
  const percent = start + (end - start) * phaseFill;
  return { label, percent, detail };
}

function phaseDefaultLabel(phase: StreamPhase): string {
  switch (phase) {
    case "generation": return "Génération du contenu par l'IA…";
    case "docx": return "Mise en forme du document Word…";
    case "persistance": return "Enregistrement du projet…";
    default: return FALLBACK_LABEL;
  }
}
