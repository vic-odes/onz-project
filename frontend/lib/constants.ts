/**
 * Constantes partagées de l'application.
 * Centralisées ici pour éviter la duplication entre composants
 * (auparavant dispersées entre Stepper.tsx et ProjectCard.tsx).
 */

export const SECTEURS = [
  "Santé",
  "Éducation",
  "Agriculture",
  "Environnement",
  "Eau & Assainissement",
  "Gouvernance",
  "Protection sociale",
  "Autre",
] as const;

export type Secteur = (typeof SECTEURS)[number];

export const BAILLEURS = [
  "AFD",
  "Union Européenne",
  "Banque Mondiale",
  "PNUD",
  "Autre",
] as const;

export type Bailleur = (typeof BAILLEURS)[number];

/**
 * Couleurs Tailwind appliquées aux badges de secteur dans les listes de projets.
 * Tout secteur absent retombe sur la classe par défaut côté composant.
 */
export const SECTOR_COLORS: Record<string, string> = {
  Santé: "bg-red-100 text-red-700",
  Éducation: "bg-blue-100 text-blue-700",
  Agriculture: "bg-yellow-100 text-yellow-700",
  Environnement: "bg-green-100 text-green-700",
  "Eau & Assainissement": "bg-cyan-100 text-cyan-700",
  Gouvernance: "bg-purple-100 text-purple-700",
  "Protection sociale": "bg-orange-100 text-orange-700",
  Autre: "bg-gray-100 text-gray-700",
};

/** Couleur pleine de la barre d'accent en haut des cartes de projet, par secteur. */
export const SECTOR_ACCENT: Record<string, string> = {
  Santé: "bg-red-400",
  Éducation: "bg-blue-400",
  Agriculture: "bg-yellow-400",
  Environnement: "bg-green-400",
  "Eau & Assainissement": "bg-cyan-400",
  Gouvernance: "bg-purple-400",
  "Protection sociale": "bg-orange-400",
  Autre: "bg-gray-400",
};

export const STEP_LABELS = [
  "Informations générales",
  "Problématique & Objectifs",
  "Planification",
  "Budget",
  "Documents de référence",
  "Confirmation",
] as const;

/**
 * Valeur spéciale du champ `bailleur` : l'utilisateur ne connaît pas encore le
 * bailleur et souhaite qu'une recherche de financement soit lancée après la
 * génération du document (voir Stepper.tsx et /recherche-financement).
 */
export const RECHERCHE_BAILLEUR_LABEL = "Recherche automatique de bailleur";

/** Libellés, couleurs et icônes des catégories de compatibilité (recherche de financement). */
export const FINANCEMENT_CATEGORIES: Record<
  string,
  { label: string; icon: string; badgeClass: string }
> = {
  tres_compatible: { label: "Très forte compatibilité", icon: "🟢", badgeClass: "bg-green-100 text-green-700 border-green-300" },
  compatible: { label: "Bonne compatibilité", icon: "🟢", badgeClass: "bg-green-50 text-green-700 border-green-200" },
  a_etudier: { label: "À étudier", icon: "🟠", badgeClass: "bg-orange-100 text-orange-700 border-orange-300" },
  faible: { label: "Faible compatibilité", icon: "🔴", badgeClass: "bg-red-100 text-red-700 border-red-300" },
  non_eligible: { label: "Non éligible", icon: "⚫", badgeClass: "bg-gray-200 text-gray-600 border-gray-300" },
};

export const FINANCEMENT_CATEGORIE_ORDER = [
  "tres_compatible",
  "compatible",
  "a_etudier",
  "faible",
  "non_eligible",
] as const;

/** Libellés de l'indicateur de fiabilité d'une opportunité de financement. */
export const FIABILITE_LABELS: Record<string, string> = {
  verifie: "✓ Source officielle vérifiée",
  a_confirmer: "⚠ À confirmer auprès du bailleur",
  information_non_disponible: "⚠ Estimation — recherche en direct indisponible",
};
