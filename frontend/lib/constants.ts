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
