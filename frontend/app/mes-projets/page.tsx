"use client";
import { useEffect, useState } from "react";
import { listProjects, ProjectSummary } from "@/lib/api";
import ProjectCard from "@/components/ProjectCard";
import Link from "next/link";

export default function MesProjetsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Impossible de charger les projets. Vérifiez que le serveur est lancé."))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = (id: number) =>
    setProjects((prev) => prev.filter((p) => p.id !== id));

  return (
    <div className="py-12 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-playfair text-4xl font-bold text-bleu-marine">
              Mes projets
            </h1>
            <p className="font-source text-gray-600 mt-1">
              Historique de vos documents générés
            </p>
          </div>
          <Link href="/nouveau-projet" className="btn-primary">
            + Nouveau projet
          </Link>
        </div>

        {loading && (
          <div className="flex justify-center py-20">
            <div className="w-10 h-10 rounded-full border-4 border-gray-200 border-t-bleu-marine animate-spin" />
          </div>
        )}

        {error && (
          <div className="card text-center py-12 border-red-200">
            <p className="text-red-500 font-source font-semibold">{error}</p>
          </div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div className="card text-center py-16">
            <p className="font-playfair text-xl text-bleu-marine mb-4">
              Aucun projet pour l'instant
            </p>
            <p className="font-source text-gray-500 mb-6">
              Créez votre premier document de projet de développement international.
            </p>
            <Link href="/nouveau-projet" className="btn-accent">
              Créer un projet
            </Link>
          </div>
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
