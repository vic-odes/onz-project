import os
import io
import base64
import json
import logging
import litellm
from dotenv import load_dotenv

load_dotenv(override=True)

litellm.drop_params = True

logger = logging.getLogger(__name__)
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

SYSTEM_PROMPT = """
Tu es un expert senior en montage de projets de développement international,
avec 20 ans d'expérience auprès de bailleurs comme l'AFD, l'Union Européenne,
la Banque Mondiale et le PNUD.

Tu maîtrises parfaitement :
- Le cadre logique (Logical Framework Approach)
- Les indicateurs SMART
- L'analyse des parties prenantes
- La gestion axée sur les résultats (GAR)
- L'analyse coût-bénéfice des projets de développement
- Les standards de rédaction de chaque bailleur

Réponds UNIQUEMENT en JSON valide, sans markdown ni backticks.
Toutes les sections doivent être rédigées en français professionnel.
Ne laisse aucune section vide. Si une information manque, complète intelligemment
sur la base du secteur et du pays fournis.
"""


def _build_user_prompt(project_data: dict, has_references: bool) -> str:
    reference_note = (
        "\nLes documents de référence joints (rapports précédents, appels à projets, "
        "guidelines du bailleur) doivent guider et enrichir le contenu généré. "
        "Tiens compte de leur contenu, de leur structure et de leur terminologie.\n"
        if has_references else ""
    )
    return f"""
Génère un document complet de projet de développement international basé sur ces informations :

{json.dumps(project_data, ensure_ascii=False, indent=2)}
{reference_note}
Réponds avec un objet JSON contenant exactement ces clés :
{{
  "introduction": "...",
  "cadre_logique": {{
    "objectif_global": "...",
    "objectifs_specifiques": [],
    "resultats": [],
    "activites": [],
    "indicateurs_smart": [],
    "sources_verification": [],
    "hypotheses": []
  }},
  "parties_prenantes": [],
  "activites_detaillees": [],
  "chronogramme": [],
  "budget": {{
    "lignes": [],
    "total_usd": 0,
    "couts_directs": 0,
    "couts_indirects": 0
  }},
  "analyse_cout_benefice": {{
    "van": 0,
    "ratio_cout_benefice": 0,
    "scenario_central": "...",
    "scenario_pessimiste": "...",
    "justification": "..."
  }},
  "risques": [],
  "communication": "...",
  "note_conceptuelle": "...",
  "resume_executif": "..."
}}

Règles importantes :
- introduction : minimum 300 mots, contexte pays + problématique + justification
- cadre_logique.objectifs_specifiques : liste de chaînes de caractères
- cadre_logique.resultats : liste de chaînes de caractères
- cadre_logique.activites : liste de chaînes de caractères
- cadre_logique.indicateurs_smart : liste de chaînes de caractères (format : Indicateur - Baseline - Cible - Délai)
- cadre_logique.sources_verification : liste de chaînes de caractères
- cadre_logique.hypotheses : liste de chaînes de caractères
- parties_prenantes : liste d'objets avec clés "nom", "role", "interet", "influence" (Faible/Moyen/Fort)
- activites_detaillees : liste d'objets avec clés "titre", "description", "responsable", "duree", "objectif_lie"
- chronogramme : liste d'objets avec clés "trimestre" (T1, T2...), "activites" (liste de chaînes)
- budget.lignes : liste d'objets avec clés "categorie", "description", "montant_usd", "pourcentage"
- risques : liste d'objets avec clés "risque", "probabilite" (Faible/Moyen/Élevé), "impact" (Faible/Moyen/Élevé), "mitigation"
- note_conceptuelle : résumé 1 page si generer_note_conceptuelle est true, sinon chaîne vide
- resume_executif : synthèse 500 mots si inclure_resume_executif est true, sinon chaîne vide
"""


def _extract_text_from_pdfs(pdfs_b64: list[str]) -> str:
    """Extrait le texte brut des PDFs encodés en base64 (fallback modèles non-vision)."""
    import pypdf

    texts = []
    for i, pdf_b64 in enumerate(pdfs_b64, 1):
        try:
            pdf_bytes = base64.b64decode(pdf_b64)
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if pages_text.strip():
                texts.append(f"--- Document de référence {i} ---\n{pages_text.strip()}")
        except Exception:
            pass
    return "\n\n".join(texts)


async def _call_llm(messages: list, extra: dict) -> str:
    logger.debug("Appel LLM — modèle=%s messages=%d extra_keys=%s", MODEL, len(messages), list(extra.keys()))
    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=messages,
            max_tokens=8000,
            temperature=0.3,
            **extra,
        )
    except Exception:
        logger.exception("Erreur lors de l'appel LiteLLM (modèle=%s)", MODEL)
        raise
    content = response.choices[0].message.content
    logger.debug("Réponse LLM reçue — finish_reason=%s content_len=%s",
                 response.choices[0].finish_reason,
                 len(content) if content else "None")
    if not content:
        logger.error("Le modèle a retourné un contenu vide (finish_reason=%s)", response.choices[0].finish_reason)
        raise ValueError("Le modèle a retourné une réponse vide.")
    raw = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if not raw:
        logger.error("Contenu vide après nettoyage des balises markdown. Contenu brut: %r", content[:200])
        raise ValueError("Le modèle a retourné une réponse vide après nettoyage des balises.")
    return raw


async def generate_project_content(project_data: dict, reference_pdfs: list[str] | None = None) -> dict:
    """
    Génère le contenu complet du projet via LiteLLM.
    Si des PDFs de référence sont fournis, ils sont envoyés directement au modèle.
    En cas d'échec (modèle non-vision), le texte est extrait et réinjecté dans le prompt.
    """
    # Paramètres Azure passés explicitement si disponibles
    extra = {}
    if os.getenv("AZURE_API_KEY"):
        extra["api_key"] = os.getenv("AZURE_API_KEY")
    if os.getenv("AZURE_API_BASE"):
        extra["api_base"] = os.getenv("AZURE_API_BASE")
    if os.getenv("AZURE_API_VERSION"):
        extra["api_version"] = os.getenv("AZURE_API_VERSION")

    user_prompt = _build_user_prompt(project_data, bool(reference_pdfs))

    # Construction des messages — avec documents natifs si PDFs fournis
    if reference_pdfs:
        content: list = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            }
            for pdf_b64 in reference_pdfs
        ]
        content.append({"type": "text", "text": user_prompt})
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    try:
        raw = await _call_llm(messages, extra)
    except Exception as e:
        # Fallback : le modèle ne supporte pas les documents — extraction texte + retry
        if reference_pdfs:
            logger.warning("Échec appel natif avec PDFs (%s) — bascule sur extraction texte", type(e).__name__)
            extracted = _extract_text_from_pdfs(reference_pdfs)
            if extracted:
                logger.info("Texte extrait des PDFs — %d caractères", len(extracted))
                fallback_prompt = (
                    user_prompt
                    + f"\n\nDocuments de référence (texte extrait) :\n{extracted}"
                )
            else:
                logger.warning("Aucun texte extrait des PDFs — génération sans documents")
                fallback_prompt = user_prompt
            fallback_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": fallback_prompt},
            ]
            raw = await _call_llm(fallback_messages, extra)
        else:
            logger.exception("Erreur génération sans PDFs — pas de fallback possible")
            raise

    try:
        result = json.loads(raw)
        logger.debug("JSON parsé avec succès — %d clés de premier niveau", len(result))
        return result
    except json.JSONDecodeError:
        logger.error("JSON invalide retourné. Début du contenu brut: %r", raw[:500])
        raise
