"use client";
import { ProjectSummary, deleteProject, downloadProject } from "@/lib/api";
import { useState } from "react";

interface ProjectCardProps {
  project: ProjectSummary;
  onDelete: (id: number) => void;
}

const sectorColors: Record<string, string> = {
  Santé: "bg-red-100 text-red-700",
  Éducation: "bg-blue-100 text-blue-700",
  Agriculture: "bg-yellow-100 text-yellow-700",
  Environnement: "bg-green-100 text-green-700",
  "Eau & Assainissement": "bg-cyan-100 text-cyan-700",
  Gouvernance: "bg-purple-100 text-purple-700",
  "Protection sociale": "bg-orange-100 text-orange-700",
  Autre: "bg-gray-100 text-gray-700",
};

export default function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Supprimer le projet "${project.nom}" ?`)) return;
    setDeleting(true);
    try {
      await deleteProject(project.id);
      onDelete(project.id);
    } catch {
      alert("Impossible de supprimer ce projet.");
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await downloadProject(project.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project.nom.replace(/\s+/g, "_")}_ONZ.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Document non disponible.");
    } finally {
      setDownloading(false);
    }
  };

  const date = new Date(project.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  const sectorClass = sectorColors[project.secteur] ?? "bg-gray-100 text-gray-700";

  return (
    <div className="card hover:shadow-lg transition-shadow flex flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-playfair text-lg font-bold text-bleu-marine leading-tight">
          {project.nom}
        </h3>
        <span
          className={`text-xs font-semibold px-2 py-1 rounded-full whitespace-nowrap font-source ${sectorClass}`}
        >
          {project.secteur}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-source text-sm text-gray-600">
        <span>🌍 {project.pays}</span>
        <span>🏦 {project.bailleur}</span>
        {project.duree_mois && <span>📅 {project.duree_mois} mois</span>}
        {project.budget_total && (
          <span>💰 ${project.budget_total.toLocaleString("fr-FR")} USD</span>
        )}
      </div>

      <p className="font-source text-xs text-gray-400">Créé le {date}</p>

      <div className="flex gap-2 mt-auto">
        {project.docx_path && (
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="flex-1 border border-vert-sauge text-vert-sauge rounded-lg py-2 text-sm font-semibold
                       hover:bg-vert-sauge hover:text-white transition-colors font-source disabled:opacity-50"
          >
            {downloading ? "..." : "⬇ Télécharger"}
          </button>
        )}
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="flex-1 border border-red-300 text-red-500 rounded-lg py-2 text-sm font-semibold
                     hover:bg-red-50 transition-colors font-source disabled:opacity-50"
        >
          {deleting ? "Suppression..." : "Supprimer"}
        </button>
      </div>
    </div>
  );
}
