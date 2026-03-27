const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ProjectFormData {
  nom: string;
  pays: string;
  secteur: string;
  bailleur: string;
  probleme_principal: string;
  objectif_global: string;
  objectifs_specifiques: string[];
  population_cible: string;
  nombre_beneficiaires: number | null;
  duree_mois: number | null;
  date_debut: string;
  contraintes: string;
  risques_identifies: string;
  budget_total: number | null;
  source_financement: string;
  part_couts_operationnels: number;
  generer_note_conceptuelle: boolean;
  inclure_resume_executif: boolean;
}

export interface ProjectSummary {
  id: number;
  nom: string;
  pays: string;
  secteur: string;
  bailleur: string;
  probleme_principal: string;
  objectif_global: string;
  budget_total: number | null;
  duree_mois: number | null;
  created_at: string;
}

export async function generateDocument(data: ProjectFormData): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/generate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    let errorMsg = "Erreur lors de la génération du document.";
    try {
      const err = await response.json();
      errorMsg = err.detail || errorMsg;
    } catch {}
    throw new Error(errorMsg);
  }

  return response.blob();
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await fetch(`${API_BASE}/api/projects/`);
  if (!response.ok) throw new Error("Impossible de charger les projets.");
  return response.json();
}

export async function getProject(id: number): Promise<ProjectSummary & { generated_content: Record<string, unknown> }> {
  const response = await fetch(`${API_BASE}/api/projects/${id}`);
  if (!response.ok) throw new Error("Projet introuvable.");
  return response.json();
}

export async function deleteProject(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/projects/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Impossible de supprimer le projet.");
}
