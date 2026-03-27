"use client";
import { useEffect, useState } from "react";

const messages = [
  "Analyse du contexte du projet...",
  "Génération du cadre logique...",
  "Construction de l'analyse des risques...",
  "Calcul du budget et analyse coût-bénéfice...",
  "Finalisation du document Word...",
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
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    if (downloadBlob || error) return;
    const interval = setInterval(() => {
      setMsgIndex((i) => (i < messages.length - 1 ? i + 1 : i));
    }, 2000);
    return () => clearInterval(interval);
  }, [downloadBlob, error]);

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

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-8">
      {/* Spinner */}
      <div className="relative w-20 h-20">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
        <div className="absolute inset-0 rounded-full border-4 border-t-bleu-marine border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        <div className="absolute inset-2 rounded-full border-4 border-t-vert-sauge border-r-transparent border-b-transparent border-l-transparent animate-spin [animation-direction:reverse] [animation-duration:1.5s]" />
      </div>

      <div className="text-center">
        <p className="font-playfair text-xl font-bold text-bleu-marine mb-2">
          Génération en cours
        </p>
        <p className="font-source text-vert-sauge font-semibold min-h-[1.5rem] transition-all duration-500">
          {messages[msgIndex]}
        </p>
      </div>

      {/* Barre de progression */}
      <div className="w-64 bg-gray-200 rounded-full h-2">
        <div
          className="bg-vert-sauge h-2 rounded-full transition-all duration-500"
          style={{ width: `${((msgIndex + 1) / messages.length) * 100}%` }}
        />
      </div>
      <p className="font-source text-xs text-gray-400">
        Cette opération peut prendre 30 à 60 secondes...
      </p>
    </div>
  );
}
