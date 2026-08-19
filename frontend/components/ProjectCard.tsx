"use client";
import { ProjectSummary, deleteProject, downloadProject, downloadBudgetExcel } from "@/lib/api";
import { SECTOR_COLORS, SECTOR_ACCENT } from "@/lib/constants";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";

interface ProjectCardProps {
  project: ProjectSummary;
  onDelete: (id: number) => void;
}

// Troncature à 2 lignes sans dépendre du plugin line-clamp de Tailwind.
const clamp2: React.CSSProperties = {
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

export default function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadingXlsx, setDownloadingXlsx] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (confirmTimer.current) clearTimeout(confirmTimer.current);
  }, []);

  const askDelete = () => {
    setError(null);
    setConfirmDelete(true);
    // Réinitialise l'état « Confirmer ? » si l'utilisateur ne tranche pas.
    confirmTimer.current = setTimeout(() => setConfirmDelete(false), 4000);
  };

  const handleDelete = async () => {
    if (confirmTimer.current) clearTimeout(confirmTimer.current);
    setDeleting(true);
    try {
      await deleteProject(project.id);
      onDelete(project.id);
    } catch {
      setError("Suppression impossible. Réessayez.");
      setConfirmDelete(false);
    } finally {
      setDeleting(false);
    }
  };

  // Déclenche le téléchargement d'un blob dans le navigateur.
  const triggerBlobDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Délai avant révocation : révoquer trop tôt annule le téléchargement sur certains navigateurs.
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const safeName = project.nom.replace(/\s+/g, "_") || "projet";

  const handleDownload = async () => {
    setError(null);
    setDownloading(true);
    try {
      const blob = await downloadProject(project.id);
      triggerBlobDownload(blob, `${safeName}_ONZ.docx`);
    } catch {
      setError("Document non disponible.");
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadExcel = async () => {
    setError(null);
    setDownloadingXlsx(true);
    try {
      const blob = await downloadBudgetExcel(project.id);
      triggerBlobDownload(blob, `${safeName}_budget_ONZ.xlsx`);
    } catch {
      setError("Budget Excel non disponible.");
    } finally {
      setDownloadingXlsx(false);
    }
  };

  const date = new Date(project.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  const sectorClass = SECTOR_COLORS[project.secteur] ?? "bg-gray-100 text-gray-700";
  const accentClass = SECTOR_ACCENT[project.secteur] ?? "bg-bleu-marine";

  const description = project.objectif_global || project.probleme_principal;

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-xl bg-white border border-gray-100 shadow-md
                        transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5">
      {/* Barre d'accent colorée par secteur */}
      <div className={`h-1.5 w-full ${accentClass}`} aria-hidden="true" />

      <div className="flex flex-1 flex-col gap-3 p-5">
        {/* En-tête : titre + badge secteur */}
        <div className="flex items-start justify-between gap-3">
          <h3
            title={project.nom}
            style={clamp2}
            className="font-playfair text-lg font-bold leading-snug text-bleu-marine"
          >
            {project.nom}
          </h3>
          <span
            className={`shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold font-source ${sectorClass}`}
          >
            {project.secteur}
          </span>
        </div>

        {/* Description : objectif global (ou problématique en repli) */}
        {description && (
          <p style={clamp2} className="font-source text-sm leading-relaxed text-gray-500">
            {description}
          </p>
        )}

        {/* Métadonnées en chips */}
        <div className="flex flex-wrap gap-2 font-source text-xs">
          <span className="inline-flex items-center gap-1 rounded-full border border-gray-100 bg-gray-50 px-2.5 py-1 text-gray-600">
            🌍 {project.pays}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-gray-100 bg-gray-50 px-2.5 py-1 text-gray-600">
            🏦 {project.bailleur}
          </span>
          {project.duree_mois != null && (
            <span className="inline-flex items-center gap-1 rounded-full border border-gray-100 bg-gray-50 px-2.5 py-1 text-gray-600">
              📅 {project.duree_mois} mois
            </span>
          )}
          {project.budget_total != null && (
            <span className="inline-flex items-center gap-1 rounded-full border border-vert-sauge/20 bg-vert-sauge/10 px-2.5 py-1 font-semibold text-vert-sauge">
              💰 {project.budget_total.toLocaleString("fr-FR")} USD
            </span>
          )}
        </div>

        {error && (
          <p role="alert" className="font-source text-xs font-semibold text-red-500">
            {error}
          </p>
        )}

        {/* Pied : date + actions */}
        <div className="mt-auto flex items-center justify-between gap-2 border-t border-gray-100 pt-3">
          <span className="font-source text-xs text-gray-400">Créé le {date}</span>

          {confirmDelete ? (
            <div className="flex items-center gap-2 font-source text-xs">
              <span className="text-gray-500">Supprimer&nbsp;?</span>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="rounded-md bg-red-500 px-2.5 py-1 font-semibold text-white transition-colors hover:bg-red-600 disabled:opacity-50"
              >
                {deleting ? "..." : "Oui"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                disabled={deleting}
                className="rounded-md border border-gray-200 px-2.5 py-1 font-semibold text-gray-500 transition-colors hover:bg-gray-50 disabled:opacity-50"
              >
                Non
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              {project.docx_path && (
                <>
                  <button
                    type="button"
                    onClick={handleDownload}
                    disabled={downloading}
                    aria-label={`Télécharger le document Word du projet ${project.nom}`}
                    className="inline-flex items-center gap-1 rounded-lg border border-vert-sauge px-3 py-1.5 text-sm font-semibold text-vert-sauge
                               transition-colors hover:bg-vert-sauge hover:text-white disabled:opacity-50 font-source"
                  >
                    {downloading ? "..." : "⬇ Word"}
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadExcel}
                    disabled={downloadingXlsx}
                    aria-label={`Télécharger le budget Excel du projet ${project.nom}`}
                    className="inline-flex items-center gap-1 rounded-lg border border-bleu-marine px-3 py-1.5 text-sm font-semibold text-bleu-marine
                               transition-colors hover:bg-bleu-marine hover:text-white disabled:opacity-50 font-source"
                  >
                    {downloadingXlsx ? "..." : "▤ Excel"}
                  </button>
                </>
              )}
              <Link
                href={`/recherche-financement/${project.id}`}
                aria-label={`Rechercher des financements pour le projet ${project.nom}`}
                className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-500
                           transition-colors hover:border-vert-sauge hover:text-vert-sauge font-source"
              >
                🔎
              </Link>
              <button
                type="button"
                onClick={askDelete}
                aria-label={`Supprimer le projet ${project.nom}`}
                className="inline-flex items-center rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-400
                           transition-colors hover:border-red-300 hover:text-red-500 disabled:opacity-50 font-source"
              >
                🗑
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
