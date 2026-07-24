import { AuthUser, clearStoredUser } from "./auth";

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
  inclure_perennisation: boolean;
  // PDFs de référence encodés en base64 (données seules, sans le préfixe data:)
  reference_pdfs?: string[];
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
  docx_path: string | null;
}

export interface SessionResponse {
  expires_in: number;
  user: AuthUser;
}

// Évaluation d'un projet (analyse bailleur + notation) — POST /api/generate/evaluation
export interface AnalyseBailleur {
  nom: string;
  priorites: string[];
  criteres_eligibilite: string[];
  montant_max_finançable: string;
  taux_cofinancement: string;
  score_compatibilite: number;
  risques_rejet: string[];
}

export interface CritereNotation {
  critere: string;
  note_sur_20: number;
  commentaire: string;
}

export interface Notation {
  criteres: CritereNotation[];
  score_total_sur_100: number;
  points_forts: string[];
  axes_amelioration: string[];
  recommandation: string;
}

export interface Evaluation {
  analyse_bailleur: AnalyseBailleur;
  notation: Notation;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// Erreur émise quand le serveur renvoie 401 ; capturée par le AuthContext pour déconnecter.
export class UnauthorizedError extends ApiError {
  constructor(message = "Session expirée. Veuillez vous reconnecter.") {
    super(message, 401);
  }
}

interface RequestOptions extends RequestInit {
  /** Si false, un 401 est renvoyé tel quel au lieu de déclencher la déconnexion
   *  globale (utile pour /login et /register où 401 = mauvais identifiants). */
  withAuth?: boolean;
}

async function apiFetch(path: string, options: RequestOptions = {}): Promise<Response> {
  const { withAuth = true, headers, ...rest } = options;
  const finalHeaders = new Headers(headers);
  // `credentials: "include"` fait envoyer/recevoir le cookie httpOnly de session.
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: finalHeaders,
    credentials: "include",
  });
  if (response.status === 401 && withAuth) {
    // Session expirée/invalide : on purge le cache user et on notifie l'app
    // (le AuthContext écoute cet événement pour rediriger vers /login).
    clearStoredUser();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("onz:unauthorized"));
    }
    throw new UnauthorizedError();
  }
  return response;
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const err = await response.json();
    if (typeof err?.detail === "string") return err.detail;
    if (Array.isArray(err?.detail) && err.detail[0]?.msg) return String(err.detail[0].msg);
  } catch {}
  return fallback;
}

// ─────────────────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<SessionResponse> {
  const response = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    withAuth: false,
  });
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response, "Connexion impossible."), response.status);
  }
  return response.json();
}

export async function register(
  email: string,
  password: string,
  full_name?: string,
): Promise<SessionResponse> {
  const response = await apiFetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: full_name || null }),
    withAuth: false,
  });
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response, "Inscription impossible."), response.status);
  }
  return response.json();
}

export async function fetchMe(): Promise<AuthUser> {
  const response = await apiFetch("/api/auth/me");
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response, "Profil indisponible."), response.status);
  }
  return response.json();
}

export async function logout(): Promise<void> {
  // Demande au backend de supprimer le cookie httpOnly de session.
  try {
    await apiFetch("/api/auth/logout", { method: "POST", withAuth: false });
  } catch {
    // Même si l'appel échoue (réseau), on poursuit la déconnexion côté client.
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Projets
// ─────────────────────────────────────────────────────────────────────────

export async function generateDocument(data: ProjectFormData): Promise<Blob> {
  const response = await apiFetch("/api/generate/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Erreur lors de la génération du document."),
      response.status,
    );
  }
  return response.blob();
}

export async function evaluateProject(data: ProjectFormData): Promise<Evaluation> {
  // On n'envoie pas les PDFs de référence : l'évaluation porte sur le concept.
  const { reference_pdfs: _ignored, ...payload } = data;
  const response = await apiFetch("/api/generate/evaluation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Erreur lors de l'évaluation du projet."),
      response.status,
    );
  }
  return response.json();
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await apiFetch("/api/projects/");
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Impossible de charger les projets."),
      response.status,
    );
  }
  return response.json();
}

export async function getProject(
  id: number,
): Promise<ProjectSummary & { generated_content: Record<string, unknown> }> {
  const response = await apiFetch(`/api/projects/${id}`);
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response, "Projet introuvable."), response.status);
  }
  return response.json();
}

export async function deleteProject(id: number): Promise<void> {
  const response = await apiFetch(`/api/projects/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Impossible de supprimer le projet."),
      response.status,
    );
  }
}

export async function downloadProject(id: number): Promise<Blob> {
  const response = await apiFetch(`/api/projects/${id}/download`);
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Document non disponible."),
      response.status,
    );
  }
  return response.blob();
}

export async function downloadBudgetExcel(id: number): Promise<Blob> {
  const response = await apiFetch(`/api/projects/${id}/budget.xlsx`);
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Budget Excel non disponible."),
      response.status,
    );
  }
  return response.blob();
}

export async function prefillFromPdf(pdfB64: string): Promise<Partial<ProjectFormData>> {
  const response = await apiFetch("/api/documents/prefill", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pdf_b64: pdfB64 }),
  });
  if (!response.ok) {
    throw new ApiError(
      await readErrorMessage(response, "Impossible d'extraire les données du PDF."),
      response.status,
    );
  }
  return response.json();
}
