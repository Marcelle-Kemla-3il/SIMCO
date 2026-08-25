"""
notion_service.py
Utilise Ollama pour analyser les questions ratées et extraire :
- Les notions à réviser
- Les compétences maîtrisées mais sous-estimées
"""
import requests
from config import settings

OLLAMA_API_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL   = settings.OLLAMA_MODEL


def extract_notion(question_text: str, is_correct: bool) -> str:
    """
    Demande à Ollama d'extraire la notion principale d'une question.
    Retourne une notion en 3-5 mots max.
    """
    prompt = f"""Quelle est la notion ou le concept principal testé par cette question de quiz ?
Réponds UNIQUEMENT par le nom du concept, en 3 à 6 mots maximum, sans phrase complète.

Question : {question_text}

Notion :"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        response.raise_for_status()
        notion = response.json().get("response", "").strip()
        # Nettoyer la réponse
        notion = notion.split('\n')[0].strip()
        notion = notion.replace('"', '').replace("'", "").strip()
        return notion if notion else "Concept non identifié"
    except Exception as e:
        print(f"⚠️ Erreur extraction notion: {e}")
        return "Concept non identifié"


def analyze_session_notions(session_data: dict) -> dict:
    """
    Analyse toutes les questions d'une session et retourne :
    - notions_to_revise   : questions ratées → notions à revoir
    - mastered_notions    : questions réussies mais sous-estimées
    - overconfident_notions: questions ratées avec haute confiance
    """
    questions       = session_data.get("questions", [])
    answers_data    = session_data.get("user_answers_data", {})
    confidence_data = session_data.get("confidence_data", {})
    behavioral_data = session_data.get("behavioral_data", {})

    notions_to_revise      = []  # faux + haute confiance ou simplement faux
    mastered_notions       = []  # juste + basse confiance
    overconfident_notions  = []  # faux + confiance > 65

    for q in questions:
        qid          = q["id"]
        question_txt = q["question"]
        correct_ans  = q["correct_answer"]
        user_ans     = answers_data.get(qid)

        if user_ans is None:
            continue

        is_correct         = user_ans == correct_ans
        declared_conf      = confidence_data.get(qid, 50)
        behavioral         = behavioral_data.get(qid, {})
        conf_observed      = behavioral.get("confidence_observed_avg", 0.5)

        # Extraire la notion via Ollama
        print(f"🔍 Extraction notion pour : {question_txt[:50]}...")
        notion = extract_notion(question_txt, is_correct)

        if not is_correct:
            entry = {
                "question": question_txt,
                "notion": notion,
                "declared_confidence": declared_conf,
                "confidence_observed": round(conf_observed * 100, 1),
                "explanation": q.get("explanation", "")
            }
            notions_to_revise.append(entry)

            if declared_conf > 65:
                overconfident_notions.append(entry)

        else:
            # Juste mais basse confiance → syndrome de l'imposteur
            if declared_conf < 40 or conf_observed < 0.4:
                mastered_notions.append({
                    "question": question_txt,
                    "notion": notion,
                    "declared_confidence": declared_conf,
                    "confidence_observed": round(conf_observed * 100, 1),
                    "explanation": q.get("explanation", "")
                })

    print(f"✅ Analyse notions terminée — "
          f"{len(notions_to_revise)} à réviser, "
          f"{len(mastered_notions)} maîtrisées sous-estimées")

    return {
        "notions_to_revise":     notions_to_revise,
        "mastered_notions":      mastered_notions,
        "overconfident_notions": overconfident_notions
    }


def generate_personalized_message(profil_ml: str, score: float, notions: dict) -> str:
    """
    Génère un message personnalisé selon le profil DK détecté.
    """
    n_revise   = len(notions.get("notions_to_revise", []))
    n_mastered = len(notions.get("mastered_notions", []))

    messages = {
        "overconfident": (
            f"⚠️ Attention — Pic de Dunning-Kruger détecté\n"
            f"Votre score réel est de {score:.0f}% mais votre confiance était élevée. "
            f"Vous avez {n_revise} notion(s) à revoir sérieusement. "
            f"La prise de conscience est la première étape vers la maîtrise."
        ),
        "impostor": (
            f"💪 Syndrome de l'imposteur détecté\n"
            f"Vous avez obtenu {score:.0f}% — c'est bien mieux que vous ne le pensez ! "
            f"Vous maîtrisez {n_mastered} notion(s) sans le savoir. "
            f"Faites confiance à vos compétences réelles."
        ),
        "calibrated": (
            f"🎯 Profil calibré — Excellente auto-évaluation\n"
            f"Votre score de {score:.0f}% correspond à votre niveau de confiance. "
            f"Continuez sur cette lancée et travaillez les {n_revise} notion(s) restantes."
        ),
        "conscious": (
            f"📚 Incompétence consciente — Bon point de départ\n"
            f"Vous avez {score:.0f}% et vous savez que vous avez des lacunes. "
            f"C'est déjà un avantage. Concentrez-vous sur les {n_revise} notion(s) identifiées."
        )
    }

    return messages.get(profil_ml, messages["calibrated"])