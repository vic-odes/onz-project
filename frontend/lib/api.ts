import { AuthUser, clearStoredAuth, getStoredToken } from "./auth";

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

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
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
  /** Si false, n'envoie pas le bearer même s'il existe (utile pour /login, /register). */
  withAuth?: boolean;
}

async function apiFetch(path: string, options: RequestOptions = {}): Promise<Response> {
  const { withAuth = true, headers, ...rest } = options;
  const finalHeaders = new Headers(headers);
  if (withAuth) {
    const token = getStoredToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...rest, headers: finalHeaders });
  if (response.status === 401 && withAuth) {
    // Token invalide ou expiré : on purge le storage. La redirection vers /login est gérée par le AuthContext.
    clearStoredAuth();
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

export async function login(email: string, password: string): Promise<TokenResponse> {
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
): Promise<TokenResponse> {
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
