"use client";
import { useState } from "react";
import { generateDocument, ProjectFormData } from "@/lib/api";
import GenerationLoader from "./GenerationLoader";

const SECTEURS = [
  "Santé",
  "Éducation",
  "Agriculture",
  "Environnement",
  "Eau & Assainissement",
  "Gouvernance",
  "Protection sociale",
  "Autre",
];

const BAILLEURS = [
  "AFD",
  "Union Européenne",
  "Banque Mondiale",
  "PNUD",
  "Autre",
];

const STEP_LABELS = [
  "Informations générales",
  "Problématique & Objectifs",
  "Planification",
  "Budget",
  "Confirmation",
];

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

export default function Stepper() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ProjectFormData>(defaultForm);
  const [generating, setGenerating] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const validateStep = (): string | null => {
    if (step === 0) {
      if (!form.nom.trim()) return "Le nom du projet est requis.";
      if (!form.pays.trim()) return "Le pays est requis.";
      if (!form.secteur) return "Veuillez choisir un secteur.";
      if (!form.bailleur) return "Veuillez choisir un bailleur.";
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
    try {
      const result = await generateDocument({
        ...form,
        objectifs_specifiques: form.objectifs_specifiques.filter((o) => o.trim()),
      });
      setBlob(result);
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
        />
        {(blob || error) && (
          <div className="flex justify-center mt-4">
            <button
              onClick={() => {
                setBlob(null);
                setError(null);
                setGenerating(false);
                setStep(0);
                setForm(defaultForm);
              }}
              className="btn-secondary"
            >
              Créer un nouveau projet
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
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
                onChange={(e) => set("bailleur", e.target.value)}
              >
                <option value="">-- Sélectionner un bailleur --</option>
                {BAILLEURS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
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

        {/* ÉTAPE 5 — CONFIRMATION */}
        {step === 4 && (
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

          {step < 4 ? (
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
