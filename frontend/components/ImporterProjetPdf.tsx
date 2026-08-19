"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { importerProjetEtRechercher, prefillFromPdf } from "@/lib/api";
import FinancementLoader from "./FinancementLoader";

const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface ReviewForm {
  nom: string;
  pays: string;
  secteur: string;
  probleme_principal: string;
  objectif_global: string;
  budget_total: number | null;
  duree_mois: number | null;
}

const emptyReview: ReviewForm = {
  nom: "",
  pays: "",
  secteur: "",
  probleme_principal: "",
  objectif_global: "",
  budget_total: null,
  duree_mois: null,
};

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Permet de rechercher un financement pour un projet monté hors de l'application :
 * importer son document PDF, extraire ses caractéristiques (comme le pré-remplissage
 * du Stepper), les vérifier, puis lancer la recherche sans passer par la génération
 * d'un nouveau document.
 */
export default function ImporterProjetPdf() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<{ name: string; b64: string } | null>(null);
  const [phase, setPhase] = useState<"idle" | "extracting" | "review" | "searching">("idle");
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewForm>(emptyReview);

  const setReviewField = <K extends keyof ReviewForm>(key: K, value: ReviewForm[K]) =>
    setReview((r) => ({ ...r, [key]: value }));

  const handleFile = async (selected: File) => {
    setError(null);
    if (selected.type !== "application/pdf") {
      setError("Seuls les fichiers PDF sont acceptés.");
      return;
    }
    if (selected.size > MAX_SIZE_BYTES) {
      setError(`"${selected.name}" dépasse ${MAX_SIZE_MB} Mo.`);
      return;
    }
    try {
      const b64 = await readFileAsBase64(selected);
      setFile({ name: selected.name, b64 });
    } catch {
      setError(`Impossible de lire "${selected.name}".`);
    }
  };

  const handleAnalyser = async () => {
    if (!file) return;
    setPhase("extracting");
    setError(null);
    try {
      const extracted = await prefillFromPdf(file.b64);
      setReview({
        nom: extracted.nom || "",
        pays: extracted.pays || "",
        secteur: extracted.secteur || "",
        probleme_principal: extracted.probleme_principal || "",
        objectif_global: extracted.objectif_global || "",
        budget_total: extracted.budget_total ?? null,
        duree_mois: extracted.duree_mois ?? null,
      });
      setPhase("review");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'analyse du document.");
      setPhase("idle");
    }
  };

  const handleRechercher = async () => {
    setPhase("searching");
    setError(null);
    try {
      const recherche = await importerProjetEtRechercher(review);
      router.push(`/recherche-financement/resultats/${recherche.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de la recherche de financement.");
      setPhase("review");
    }
  };

  if (phase === "extracting") {
    return (
      <div className="card py-10 text-center">
        <div className="w-10 h-10 mx-auto rounded-full border-4 border-gray-200 border-t-bleu-marine animate-spin mb-4" />
        <p className="font-source text-bleu-marine font-semibold">Analyse du document…</p>
      </div>
    );
  }

  if (phase === "searching") {
    return (
      <div className="card">
        <FinancementLoader error={error} />
      </div>
    );
  }

  if (phase === "review") {
    const canSubmit = review.nom.trim().length > 0 && review.pays.trim().length > 0;
    return (
      <div className="card">
        <p className="font-playfair text-lg font-bold text-bleu-marine mb-1">
          Vérifiez les informations extraites
        </p>
        <p className="font-source text-sm text-gray-500 mb-5">
          Corrigez si besoin avant de lancer la recherche de financement.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Nom du projet *</label>
            <input
              className="input-field"
              value={review.nom}
              onChange={(e) => setReviewField("nom", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Pays / zone d&apos;intervention *</label>
            <input
              className="input-field"
              value={review.pays}
              onChange={(e) => setReviewField("pays", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Secteur</label>
            <input
              className="input-field"
              value={review.secteur}
              onChange={(e) => setReviewField("secteur", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Budget total (USD)</label>
            <input
              type="number"
              className="input-field"
              value={review.budget_total ?? ""}
              onChange={(e) => setReviewField("budget_total", e.target.value ? Number(e.target.value) : null)}
            />
          </div>
          <div>
            <label className="label">Durée (mois)</label>
            <input
              type="number"
              className="input-field"
              value={review.duree_mois ?? ""}
              onChange={(e) => setReviewField("duree_mois", e.target.value ? Number(e.target.value) : null)}
            />
          </div>
        </div>
        <div className="mt-4">
          <label className="label">Problématique principale</label>
          <textarea
            className="input-field"
            rows={2}
            value={review.probleme_principal}
            onChange={(e) => setReviewField("probleme_principal", e.target.value)}
          />
        </div>
        <div className="mt-4">
          <label className="label">Objectif global</label>
          <textarea
            className="input-field"
            rows={2}
            value={review.objectif_global}
            onChange={(e) => setReviewField("objectif_global", e.target.value)}
          />
        </div>

        {error && <p role="alert" className="font-source text-sm text-red-600 mt-4">{error}</p>}

        <div className="flex justify-between items-center mt-6">
          <button type="button" className="btn-secondary" onClick={() => { setPhase("idle"); setFile(null); }}>
            ← Recommencer
          </button>
          <button
            type="button"
            className="btn-accent disabled:opacity-50 disabled:cursor-default"
            disabled={!canSubmit}
            onClick={handleRechercher}
          >
            🔎 Rechercher les financements
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${dragging ? "border-vert-sauge bg-green-50" : "border-gray-300 hover:border-bleu-marine hover:bg-gray-50"}`}
      >
        <div className="text-3xl mb-2">📄</div>
        <p className="font-source font-semibold text-bleu-marine text-sm">
          Glissez le document de votre projet ici ou cliquez pour le sélectionner
        </p>
        <p className="font-source text-xs text-gray-400 mt-1">PDF uniquement — {MAX_SIZE_MB} Mo max</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      {error && <p role="alert" className="font-source text-sm text-red-500 mt-3">{error}</p>}

      {file && (
        <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 mt-3">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-lg">📎</span>
            <p className="font-source text-sm font-semibold text-bleu-marine truncate">{file.name}</p>
          </div>
          <button
            onClick={() => setFile(null)}
            className="text-gray-400 hover:text-red-500 font-bold text-xl px-2 flex-shrink-0"
            title="Supprimer"
          >
            ×
          </button>
        </div>
      )}

      <div className="flex justify-end mt-4">
        <button type="button" className="btn-primary disabled:opacity-50" disabled={!file} onClick={handleAnalyser}>
          Analyser le document
        </button>
      </div>
    </div>
  );
}
