"use client";
import { useEffect, useState } from "react";

// Étapes affichées en boucle pendant la génération (le backend ne streame pas de
// progression : on simule une progression douce pour rassurer l'utilisateur).
const STEP_LABELS = [
  "Analyse du contexte du projet…",
  "Génération du cadre logique…",
  "Construction de l'analyse des risques…",
  "Calcul du budget…",
  "Finalisation du document Word…",
];

interface GenerationLoaderProps {
  onDownload?: () => void;
  downloadBlob?: Blob | null;
  fileName?: string;
  error?: string | null;
}

export default function GenerationLoader({
  onDownload,
  downloadBlob,
  fileName = "projet_ONZ.docx",
  error,
}: GenerationLoaderProps) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (downloadBlob || error) return;
    const interval = setInterval(() => setTick((t) => t + 1), 1500);
    return () => clearInterval(interval);
  }, [downloadBlob, error]);

  // URL objet créée une seule fois par blob et révoquée au démontage (évite la fuite mémoire).
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!downloadBlob) {
      setBlobUrl(null);
      return;
    }
    const url = URL.createObjectURL(downloadBlob);
    setBlobUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [downloadBlob]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center text-3xl">
          ✗
        </div>
        <p className="font-playfair text-xl font-bold text-red-600">Erreur de génération</p>
        <p role="alert" className="font-source text-gray-600 text-center max-w-md">{error}</p>
      </div>
    );
  }

  if (downloadBlob && blobUrl) {
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
          href={blobUrl}
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

  const label = STEP_LABELS[Math.min(tick, STEP_LABELS.length - 1)];
  const percent = ((Math.min(tick, STEP_LABELS.length - 1) + 1) / STEP_LABELS.length) * 100;

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
      <p className="font-source text-xs text-gray-400">
        Cette opération peut prendre plusieurs minutes selon les documents joints — vous pouvez
        laisser cet onglet ouvert, la génération continue côté serveur.
      </p>
    </div>
  );
}
