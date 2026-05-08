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

// ─────────────────────────────────────────────────────────────────────────
// Génération en streaming (SSE)
// ─────────────────────────────────────────────────────────────────────────

export type StreamPhase = "generation" | "docx" | "persistance";

export interface StreamProgressEvent {
  type: "phase" | "progress";
  phase: StreamPhase;
  /** Libellé localisé renvoyé par le backend (présent pour `phase`). */
  label?: string;
  /** Caractères reçus du LLM (présent pour `progress` pendant la phase generation). */
  chars?: number;
}

export interface StreamDoneEvent {
  project_id: number | null;
  filename: string;
  chars: number;
}

export interface StreamCallbacks {
  onProgress?: (event: StreamProgressEvent) => void;
  /** Permet d'annuler le stream depuis l'extérieur. */
  signal?: AbortSignal;
}

/**
 * Lance le pipeline de génération en SSE.
 *
 * Résolu avec le payload `done` (project_id + filename) — l'appelant peut alors
 * télécharger le `.docx` via `downloadProject(project_id)`.
 *
 * Rejette avec `ApiError` :
 *   - status 0 si le serveur émet un event `error` (échec applicatif),
 *   - status HTTP réel si la connexion échoue avant le stream.
 */
export async function generateDocumentStream(
  data: ProjectFormData,
  callbacks: StreamCallbacks = {},
): Promise<StreamDoneEvent> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}/api/generate/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
    signal: callbacks.signal,
  });

  if (response.status === 401) {
    clearStoredAuth();
    throw new UnauthorizedError();
  }
  if (!response.ok || !response.body) {
    throw new ApiError(
      await readErrorMessage(response, "Erreur lors de la génération du document."),
      response.status,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let done: StreamDoneEvent | null = null;

  // Parser SSE minimal : un event = un bloc séparé par "\n\n", lignes "event:" + "data:".
  while (true) {
    const { value, done: streamDone } = await reader.read();
    if (streamDone) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const record = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      let eventName = "message";
      let dataLine = "";
      for (const line of record.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (!dataLine) continue;

      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(dataLine);
      } catch {
        continue;  // event mal formé : on ignore plutôt que de tout casser
      }

      if (eventName === "error") {
        throw new ApiError(
          (payload.message as string) || "Erreur de génération.",
          0,
        );
      }
      if (eventName === "done") {
        done = payload as unknown as StreamDoneEvent;
        continue;
      }
      if (eventName === "phase") {
        callbacks.onProgress?.({
          type: "phase",
          phase: payload.name as StreamPhase,
          label: payload.label as string,
        });
      } else if (eventName === "progress") {
        callbacks.onProgress?.({
          type: "progress",
          phase: payload.phase as StreamPhase,
          chars: payload.chars as number,
        });
      }
    }
  }

  if (!done) {
    throw new ApiError("Le stream s'est interrompu avant la fin de la génération.", 0);
  }
  return done;
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
