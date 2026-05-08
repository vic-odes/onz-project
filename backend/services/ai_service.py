import io
import base64
import json
import logging
import os

from services import llm_client

logger = logging.getLogger(__name__)

# Limite du texte extrait pour éviter le dépassement de contexte (indépendante du modèle)
_MAX_EXTRACTED_CHARS = 3000


def _compute_max_tokens(supports_native_pdf: bool) -> int:
    """Sortie : 8000 tokens si Claude (réponses longues OK), sinon plafonné par LLM_MAX_TOKENS."""
    if supports_native_pdf:
        return 8000
    return int(os.getenv("LLM_MAX_TOKENS", "4096"))

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


async def generate_project_content(project_data: dict, reference_pdfs: list[str] | None = None) -> dict:
    """
    Génère le contenu complet du projet via LiteLLM.
    Si des PDFs de référence sont fournis, ils sont envoyés directement au modèle.
    En cas d'échec (modèle non-vision), le texte est extrait et réinjecté dans le prompt.

    Les capacités du modèle (PDF natif, max_tokens) sont relues à chaque appel pour
    permettre le hot-swap de `LLM_MODEL` sans redémarrage.
    """
    supports_native_pdf = llm_client.supports_native_pdf()
    max_tokens = _compute_max_tokens(supports_native_pdf)
    user_prompt = _build_user_prompt(project_data, bool(reference_pdfs))

    # Construction des messages
    # Les blocs "document" natifs ne sont supportés que par Anthropic/Claude
    if reference_pdfs and supports_native_pdf:
        logger.debug("Mode PDF natif (Claude) — %d document(s)", len(reference_pdfs))
        pdf_blocks: list = [
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
        pdf_blocks.append({"type": "text", "text": user_prompt})
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pdf_blocks},
        ]
    elif reference_pdfs:
        # Modèle non-Claude : extraction directe sans aller-retour inutile
        logger.debug("Mode extraction texte (non-Claude) — %d document(s)", len(reference_pdfs))
        extracted = _extract_text_from_pdfs(reference_pdfs)
        if extracted:
            extracted_truncated = extracted[:_MAX_EXTRACTED_CHARS]
            if len(extracted) > _MAX_EXTRACTED_CHARS:
                logger.info("Texte extrait tronqué à %d/%d caractères", _MAX_EXTRACTED_CHARS, len(extracted))
            else:
                logger.info("Texte extrait — %d caractères", len(extracted))
            user_prompt = user_prompt + f"\n\nDocuments de référence (texte extrait) :\n{extracted_truncated}"
        else:
            logger.warning("Aucun texte extrait des PDFs — génération sans documents")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    try:
        raw = await llm_client.call_llm(messages, max_tokens=max_tokens)
    except Exception as e:
        # Fallback uniquement pour Claude (si le modèle refuse les document blocks)
        if reference_pdfs and supports_native_pdf:
            logger.warning("Échec PDF natif Claude (%s) — bascule sur extraction texte", type(e).__name__)
            extracted = _extract_text_from_pdfs(reference_pdfs)
            fallback_prompt = user_prompt
            if extracted:
                extracted_truncated = extracted[:_MAX_EXTRACTED_CHARS]
                logger.info("Texte extrait (fallback) — %d caractères", len(extracted_truncated))
                fallback_prompt = user_prompt + f"\n\nDocuments de référence (texte extrait) :\n{extracted_truncated}"
            fallback_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": fallback_prompt},
            ]
            raw = await llm_client.call_llm(fallback_messages, max_tokens=max_tokens)
        else:
            logger.exception("Erreur génération — pas de fallback possible")
            raise

    result = llm_client.parse_json_response(raw)
    logger.debug("JSON parsé avec succès — %d clés de premier niveau", len(result))

    # Validation Pydantic : top-level strict, nested permissif. Évite les sections
    # silencieusement vides côté docx_service quand le modèle a oublié des clés.
    from schemas.generated import GeneratedContent
    validated = GeneratedContent.model_validate(result)
    logger.info(
        "Sortie LLM validée — %d parties_prenantes, %d activités, %d risques",
        len(validated.parties_prenantes), len(validated.activites_detaillees), len(validated.risques),
    )
    return validated.model_dump()
