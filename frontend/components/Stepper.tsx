"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, downloadProject, generateDocumentStream, prefillFromPdf, ProjectFormData, StreamProgressEvent } from "@/lib/api";
import { BAILLEURS, SECTEURS, STEP_LABELS } from "@/lib/constants";
import GenerationLoader from "./GenerationLoader";
import PdfUpload from "./PdfUpload";

// Versionner la clé permet d'invalider proprement les anciens snapshots
// si la forme du formulaire change entre deux releases.
const DRAFT_STORAGE_KEY = "onz_form_draft_v1";

interface FormDraft {
  step: number;
  form: ProjectFormData;
  bailleurCustom: string;
}

const defaultForm: ProjectFormData = {
  nom: "",
  pays: "",
  secteur: "",
  bailleur: "",
  probleme_principal: "",
  objectif_global: "",
  objectifs_specifiques: [""],
  population_cible: "",
  nombre_beneficiaires: null,
  duree_mois: null,
  date_debut: "",
  contraintes: "",
  risques_identifies: "",
  budget_total: null,
  source_financement: "",
  part_couts_operationnels: 30,
  generer_note_conceptuelle: false,
  inclure_resume_executif: false,
};

interface PdfFile {
  name: string;
  sizeKb: number;
  b64: string;
}

export default function Stepper() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ProjectFormData>(defaultForm);
  const [bailleurCustom, setBailleurCustom] = useState("");
  const [budgetPdfs, setBudgetPdfs] = useState<PdfFile[]>([]);
  const [referencePdfs, setReferencePdfs] = useState<PdfFile[]>([]);
  const [prefilling, setPrefilling] = useState(false);
  const [prefillError, setPrefillError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<StreamProgressEvent | null>(null);
  const [draftRestored, setDraftRestored] = useState(false);
  const draftLoaded = useRef(false);

  // Restauration du brouillon au montage (avant d'autoriser l'écriture).
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
      if (raw) {
        const draft = JSON.parse(raw) as FormDraft;
        if (draft?.form && typeof draft.form === "object") {
          setForm({ ...defaultForm, ...draft.form });
          setBailleurCustom(draft.bailleurCustom ?? "");
          if (typeof draft.step === "number" && draft.step >= 0 && draft.step <= 5) {
            setStep(draft.step);
          }
          setDraftRestored(true);
        }
      }
    } catch {
      // Snapshot corrompu — on ignore et on repart de zéro.
    } finally {
      draftLoaded.current = true;
    }
  }, []);

  // Persistance automatique : on n'écrit qu'après la restauration initiale
  // pour éviter d'écraser le brouillon avec defaultForm au premier render.
  useEffect(() => {
    if (!draftLoaded.current || typeof window === "undefined") return;
    if (generating || blob) return;
    try {
      const draft: FormDraft = { step, form, bailleurCustom };
      window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
    } catch {
      // Quota dépassé / mode privé : pas critique, on n'interrompt pas l'utilisateur.
    }
  }, [step, form, bailleurCustom, generating, blob]);

  const clearDraft = () => {
    if (typeof window !== "undefined") {
      try { window.localStorage.removeItem(DRAFT_STORAGE_KEY); } catch { /* noop */ }
    }
    setDraftRestored(false);
  };

  const set = (field: keyof ProjectFormData, value: unknown) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const addObjectif = () =>
    set("objectifs_specifiques", [...form.objectifs_specifiques, ""]);

  const removeObjectif = (i: number) =>
    set(
      "objectifs_specifiques",
      form.objectifs_specifiques.filter((_, idx) => idx !== i)
    );

  const updateObjectif = (i: number, val: string) =>
    set(
      "objectifs_specifiques",
      form.objectifs_specifiques.map((o, idx) => (idx === i ? val : o))
    );

  const handlePrefill = async (file: File) => {
    setPrefillError(null);
    setPrefilling(true);
    try {
      const b64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve((reader.result as string).split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      const extracted = await prefillFromPdf(b64);
      // Pré-remplir les champs du formulaire avec les données extraites
      setForm((prev) => ({
        ...prev,
        ...(extracted.nom && { nom: extracted.nom }),
        ...(extracted.pays && { pays: extracted.pays }),
        ...(extracted.secteur && { secteur: extracted.secteur }),
        ...(extracted.bailleur && { bailleur: (BAILLEURS as readonly string[]).includes(extracted.bailleur) ? extracted.bailleur : "Autre" }),
        ...(extracted.probleme_principal && { probleme_principal: extracted.probleme_principal }),
        ...(extracted.objectif_global && { objectif_global: extracted.objectif_global }),
        ...(extracted.objectifs_specifiques?.length && { objectifs_specifiques: extracted.objectifs_specifiques }),
        ...(extracted.population_cible && { population_cible: extracted.population_cible }),
        ...(extracted.nombre_beneficiaires && { nombre_beneficiaires: extracted.nombre_beneficiaires }),
        ...(extracted.duree_mois && { duree_mois: extracted.duree_mois }),
        ...(extracted.budget_total && { budget_total: extracted.budget_total }),
        ...(extracted.source_financement && { source_financement: extracted.source_financement }),
        ...(extracted.contraintes && { contraintes: extracted.contraintes }),
        ...(extracted.risques_identifies && { risques_identifies: extracted.risques_identifies }),
      }));
      // Si le bailleur extrait n'est pas dans la liste, le mettre dans le champ custom
      if (extracted.bailleur && !(BAILLEURS as readonly string[]).includes(extracted.bailleur)) {
        setBailleurCustom(extracted.bailleur);
      }
    } catch (e) {
      setPrefillError(e instanceof Error ? e.message : "Erreur lors de l'extraction");
    } finally {
      setPrefilling(false);
    }
  };

  const validateStep = (): string | null => {
    if (step === 0) {
      if (!form.nom.trim()) return "Le nom du projet est requis.";
      if (!form.pays.trim()) return "Le pays est requis.";
      if (!form.secteur) return "Veuillez choisir un secteur.";
      if (!form.bailleur) return "Veuillez choisir un bailleur.";
      if (form.bailleur === "Autre" && !bailleurCustom.trim()) return "Veuillez préciser le nom du bailleur.";
    }
    if (step === 1) {
      if (!form.probleme_principal.trim()) return "La problématique est requise.";
      if (!form.objectif_global.trim()) return "L'objectif global est requis.";
    }
    return null;
  };

  const handleNext = () => {
    const err = validateStep();
    if (err) { alert(err); return; }
    setStep((s) => s + 1);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setBlob(null);
    setProgress(null);
    const allPdfs = [...budgetPdfs, ...referencePdfs];
    try {
      const done = await generateDocumentStream(
        {
          ...form,
          bailleur: form.bailleur === "Autre" ? bailleurCustom : form.bailleur,
          objectifs_specifiques: form.objectifs_specifiques.filter((o) => o.trim()),
          reference_pdfs: allPdfs.length > 0 ? allPdfs.map((f) => f.b64) : undefined,
        },
        { onProgress: setProgress },
      );
      // Le stream renvoie l'id du projet : on télécharge ensuite le .docx via /projects/{id}/download.
      // Si la persistance a échoué côté backend, project_id sera null — peu probable mais on remonte alors une erreur claire.
      if (done.project_id == null) {
        throw new ApiError("Document généré mais non sauvegardé. Réessayez.", 0);
      }
      const docxBlob = await downloadProject(done.project_id);
      setBlob(docxBlob);
      clearDraft();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setGenerating(false);
    }
  };

  const fileName = `${form.nom.replace(/\s+/g, "_") || "projet"}_ONZ.docx`;

  if (generating || blob || error) {
    return (
      <div className="card max-w-2xl mx-auto mt-10">
        <GenerationLoader
          downloadBlob={blob}
          fileName={fileName}
          error={error}
          progress={progress}
        />
        {blob && (
          <div className="flex justify-center mt-4">
            <button
              onClick={() => {
                setBlob(null);
                setError(null);
                setGenerating(false);
                setProgress(null);
                setStep(0);
                setForm(defaultForm);
                setBailleurCustom("");
                setBudgetPdfs([]);
                setReferencePdfs([]);
                setPrefillError(null);
                clearDraft();
              }}
              className="btn-secondary"
            >
              Créer un nouveau projet
            </button>
          </div>
        )}
        {error && (
          <div className="flex justify-center gap-3 mt-4 flex-wrap">
            <button
              onClick={() => { setProgress(null); handleGenerate(); }}
              className="btn-primary"
            >
              ↺ Réessayer
            </button>
            <button
              onClick={() => { setError(null); setProgress(null); setStep(5); }}
              className="btn-secondary"
            >
              ← Modifier le projet
            </button>
            <button
              onClick={() => {
                setError(null);
                setProgress(null);
                setStep(0);
                setForm(defaultForm);
                setBailleurCustom("");
                setBudgetPdfs([]);
                setReferencePdfs([]);
                setPrefillError(null);
                clearDraft();
              }}
              className="btn-secondary"
            >
              Nouveau projet
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {draftRestored && (
        <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-vert-sauge/40 bg-vert-sauge/10 px-4 py-2 font-source text-sm text-bleu-marine">
          <span>↻ Brouillon restauré automatiquement.</span>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setDraftRestored(false)}
              className="text-xs font-semibold text-bleu-marine hover:underline"
            >
              Continuer
            </button>
            <button
              type="button"
              onClick={() => {
                setForm(defaultForm);
                setBailleurCustom("");
                setStep(0);
                clearDraft();
              }}
              className="text-xs font-semibold text-red-500 hover:underline"
            >
              Réinitialiser
            </button>
          </div>
        </div>
      )}

      {/* Barre d'étapes */}
      <div className="flex items-center mb-8">
        {STEP_LABELS.map((label, i) => (
          <div key={i} className="flex items-center flex-1 last:flex-none">
            <button
              onClick={() => i < step && setStep(i)}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                font-source transition-colors
                ${i < step
                  ? "bg-vert-sauge text-white cursor-pointer"
                  : i === step
                  ? "bg-bleu-marine text-white"
                  : "bg-gray-200 text-gray-500 cursor-default"
                }`}
            >
              {i < step ? "✓" : i + 1}
            </button>
            {i < STEP_LABELS.length - 1 && (
              <div
                className={`flex-1 h-1 mx-1 rounded transition-colors ${
                  i < step ? "bg-vert-sauge" : "bg-gray-200"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="font-playfair text-2xl font-bold text-bleu-marine mb-6">
          Étape {step + 1} — {STEP_LABELS[step]}
        </h2>

        {/* ÉTAPE 1 */}
        {step === 0 && (
          <div className="flex flex-col gap-5">
            {/* Pré-remplissage depuis un PDF */}
            <div className="border border-dashed border-bleu-marine/30 rounded-lg p-4 bg-bleu-marine/5">
              <p className="label mb-2">Pré-remplir depuis un PDF existant <span className="font-normal text-gray-400">(optionnel)</span></p>
              <p className="font-source text-xs text-gray-500 mb-3">
                Importez un document de projet, appel à projets ou note conceptuelle — les champs seront remplis automatiquement.
              </p>
              <label className={`inline-flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border font-source text-sm font-semibold transition-colors
                ${prefilling ? "bg-gray-100 text-gray-400 border-gray-200 pointer-events-none" : "bg-white border-bleu-marine text-bleu-marine hover:bg-bleu-marine hover:text-white"}`}>
                {prefilling ? "Extraction en cours…" : "📂 Choisir un PDF"}
                <input
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  disabled={prefilling}
                  onChange={(e) => e.target.files?.[0] && handlePrefill(e.target.files[0])}
                />
              </label>
              {prefillError && <p className="font-source text-xs text-red-500 mt-2">{prefillError}</p>}
              {!prefilling && !prefillError && form.nom && (
                <p className="font-source text-xs text-vert-sauge font-semibold mt-2">✓ Formulaire pré-rempli — vérifiez et complétez si besoin</p>
              )}
            </div>

            <div>
              <label className="label">Nom du projet *</label>
              <input
                className="input-field"
                placeholder="Ex. : Accès à l'eau potable en milieu rural"
                value={form.nom}
                onChange={(e) => set("nom", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Pays / Zone d'intervention *</label>
              <input
                className="input-field"
                placeholder="Ex. : Mali, Sénégal, Haïti..."
                value={form.pays}
                onChange={(e) => set("pays", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Secteur *</label>
              <select
                className="input-field"
                value={form.secteur}
                onChange={(e) => set("secteur", e.target.value)}
              >
                <option value="">-- Sélectionner un secteur --</option>
                {SECTEURS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Bailleur cible *</label>
              <select
                className="input-field"
                value={form.bailleur}
                onChange={(e) => { set("bailleur", e.target.value); if (e.target.value !== "Autre") setBailleurCustom(""); }}
              >
                <option value="">-- Sélectionner un bailleur --</option>
                {BAILLEURS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
              {form.bailleur === "Autre" && (
                <input
                  className="input-field mt-2"
                  placeholder="Nom du bailleur *"
                  value={bailleurCustom}
                  onChange={(e) => setBailleurCustom(e.target.value)}
                />
              )}
            </div>
          </div>
        )}

        {/* ÉTAPE 2 */}
        {step === 1 && (
          <div className="flex flex-col gap-5">
            <div>
              <label className="label">Problème principal *</label>
              <textarea
                className="input-field resize-none"
                rows={4}
                placeholder="Décrivez le problème central que le projet vise à résoudre..."
                value={form.probleme_principal}
                onChange={(e) => set("probleme_principal", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Objectif global *</label>
              <textarea
                className="input-field resize-none"
                rows={3}
                placeholder="Quel est l'impact à long terme visé par ce projet ?"
                value={form.objectif_global}
                onChange={(e) => set("objectif_global", e.target.value)}
              />
            </div>

            <div>
              <label className="label">Objectifs spécifiques</label>
              <div className="flex flex-col gap-2">
                {form.objectifs_specifiques.map((obj, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      className="input-field flex-1"
                      placeholder={`Objectif spécifique ${i + 1}`}
                      value={obj}
                      onChange={(e) => updateObjectif(i, e.target.value)}
                    />
                    {form.objectifs_specifiques.length > 1 && (
                      <button
                        onClick={() => removeObjectif(i)}
                        className="text-red-400 hover:text-red-600 font-bold text-xl px-2"
                        title="Supprimer"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                onClick={addObjectif}
                className="mt-2 text-vert-sauge font-source font-semibold text-sm hover:underline"
              >
                + Ajouter un objectif
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Population cible</label>
                <input
                  className="input-field"
                  placeholder="Ex. : Agriculteurs ruraux"
                  value={form.population_cible}
                  onChange={(e) => set("population_cible", e.target.value)}
                />
              </div>
              <div>
                <label className="label">Nombre de bénéficiaires</label>
                <input
                  type="number"
                  className="input-field"
                  placeholder="Ex. : 50000"
                  value={form.nombre_beneficiaires ?? ""}
                  onChange={(e) =>
                    set("nombre_beneficiaires", e.target.value ? parseInt(e.target.value) : null)
                  }
                />
              </div>
            </div>
          </div>
        )}

        {/* ÉTAPE 3 */}
        {step === 2 && (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Durée du projet (mois)</label>
                <input
                  type="number"
                  className="input-field"
                  placeholder="Ex. : 24"
                  min={1}
                  max={120}
                  value={form.duree_mois ?? ""}
                  onChange={(e) =>
                    set("duree_mois", e.target.value ? parseInt(e.target.value) : null)
                  }
                />
              </div>
              <div>
                <label className="label">Date de début souhaitée</label>
                <input
                  type="date"
                  className="input-field"
                  value={form.date_debut}
                  onChange={(e) => set("date_debut", e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="label">Contraintes connues</label>
              <textarea
                className="input-field resize-none"
                rows={3}
                placeholder="Contraintes géographiques, institutionnelles, climatiques..."
                value={form.contraintes}
                onChange={(e) => set("contraintes", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Risques identifiés</label>
              <textarea
                className="input-field resize-none"
                rows={3}
                placeholder="Risques politiques, financiers, opérationnels..."
                value={form.risques_identifies}
                onChange={(e) => set("risques_identifies", e.target.value)}
              />
            </div>
          </div>
        )}

        {/* ÉTAPE 4 */}
        {step === 3 && (
          <div className="flex flex-col gap-5">
            {/* Import PDF budget */}
            <div className="border border-dashed border-vert-sauge/40 rounded-lg p-4 bg-vert-sauge/5">
              <p className="label mb-1">Importer un PDF budgétaire <span className="font-normal text-gray-400">(optionnel)</span></p>
              <p className="font-source text-xs text-gray-500 mb-3">
                Joignez un budget existant (tableau, devis, document financier) — l&apos;IA l&apos;utilisera pour construire le budget du projet.
              </p>
              <PdfUpload files={budgetPdfs} onChange={setBudgetPdfs} />
            </div>

            <div>
              <label className="label">Budget total estimé (USD)</label>
              <input
                type="number"
                className="input-field"
                placeholder="Ex. : 500000 (optionnel)"
                min={0}
                value={form.budget_total ?? ""}
                onChange={(e) =>
                  set("budget_total", e.target.value ? parseFloat(e.target.value) : null)
                }
              />
            </div>
            <div>
              <label className="label">Source de financement principale</label>
              <input
                className="input-field"
                placeholder="Ex. : Subvention AFD + cofinancement État"
                value={form.source_financement}
                onChange={(e) => set("source_financement", e.target.value)}
              />
            </div>
            <div>
              <label className="label">
                Part des coûts opérationnels : {form.part_couts_operationnels}%
              </label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                className="w-full accent-vert-sauge mt-1"
                value={form.part_couts_operationnels}
                onChange={(e) => set("part_couts_operationnels", parseInt(e.target.value))}
              />
              <div className="flex justify-between text-xs text-gray-400 font-source mt-1">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
          </div>
        )}

        {/* ÉTAPE 5 — DOCUMENTS DE RÉFÉRENCE */}
        {step === 4 && (
          <div className="flex flex-col gap-5">
            <p className="font-source text-sm text-gray-600">
              Optionnel — Joignez des PDFs de référence (rapports précédents, appels à projets,
              guidelines du bailleur). L&apos;IA analysera leur contenu, leurs schémas et leurs
              tableaux pour enrichir le document généré.
            </p>
            <PdfUpload files={referencePdfs} onChange={setReferencePdfs} />
          </div>
        )}

        {/* ÉTAPE 6 — CONFIRMATION */}
        {step === 5 && (
          <div className="flex flex-col gap-5">
            <div className="bg-gray-50 rounded-lg p-4 font-source text-sm space-y-2">
              <h3 className="font-playfair text-base font-bold text-bleu-marine mb-3">
                Récapitulatif du projet
              </h3>
              {[
                ["Nom", form.nom],
                ["Pays", form.pays],
                ["Secteur", form.secteur],
                ["Bailleur", form.bailleur],
                ["Durée", form.duree_mois ? `${form.duree_mois} mois` : "—"],
                ["Budget", form.budget_total ? `$${form.budget_total.toLocaleString()} USD` : "—"],
                ["Population cible", form.population_cible || "—"],
                ["Bénéficiaires", form.nombre_beneficiaires?.toLocaleString() || "—"],
                ["Source financement", form.source_financement || "—"],
                ["Coûts opérationnels", `${form.part_couts_operationnels}%`],
              ].map(([key, val]) => (
                <div key={key} className="flex gap-2">
                  <span className="font-semibold text-bleu-marine w-44 flex-shrink-0">{key} :</span>
                  <span className="text-gray-700">{val}</span>
                </div>
              ))}
              {form.objectifs_specifiques.filter((o) => o.trim()).length > 0 && (
                <div>
                  <span className="font-semibold text-bleu-marine">Objectifs spécifiques :</span>
                  <ul className="list-disc ml-5 mt-1 text-gray-700">
                    {form.objectifs_specifiques.filter((o) => o.trim()).map((o, i) => (
                      <li key={i}>{o}</li>
                    ))}
                  </ul>
                </div>
              )}
              {(budgetPdfs.length > 0 || referencePdfs.length > 0) && (
                <div className="flex gap-2">
                  <span className="font-semibold text-bleu-marine w-44 flex-shrink-0">Documents PDF :</span>
                  <span className="text-vert-sauge font-semibold">
                    {budgetPdfs.length + referencePdfs.length} fichier{budgetPdfs.length + referencePdfs.length > 1 ? "s" : ""} joint{budgetPdfs.length + referencePdfs.length > 1 ? "s" : ""}
                    {budgetPdfs.length > 0 && referencePdfs.length > 0 && ` (${budgetPdfs.length} budget, ${referencePdfs.length} référence)`}
                    {budgetPdfs.length > 0 && referencePdfs.length === 0 && ` budget`}
                    {budgetPdfs.length === 0 && referencePdfs.length > 0 && ` référence`}
                  </span>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 pt-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 accent-bleu-marine"
                  checked={form.generer_note_conceptuelle}
                  onChange={(e) => set("generer_note_conceptuelle", e.target.checked)}
                />
                <span className="font-source text-sm text-bleu-marine font-semibold">
                  Générer une note conceptuelle (résumé 1 page)
                </span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 accent-bleu-marine"
                  checked={form.inclure_resume_executif}
                  onChange={(e) => set("inclure_resume_executif", e.target.checked)}
                />
                <span className="font-source text-sm text-bleu-marine font-semibold">
                  Inclure un résumé exécutif (synthèse 500 mots)
                </span>
              </label>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8">
          <button
            onClick={() => setStep((s) => s - 1)}
            disabled={step === 0}
            className="btn-secondary disabled:opacity-40 disabled:cursor-default"
          >
            ← Précédent
          </button>

          {step < 5 ? (
            <button onClick={handleNext} className="btn-primary">
              Suivant →
            </button>
          ) : (
            <button onClick={handleGenerate} className="btn-accent text-lg px-8">
              ✦ Générer le document IA
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
