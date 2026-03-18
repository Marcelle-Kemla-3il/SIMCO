from typing import List, Dict, Optional

# Simple fallback question bank for local generation.
# This module is used when LLM generation fails or for local backup.

def generate_questions_by_subject(
    subject: str,
    level: str,
    num_questions: int,
    class_level: Optional[str] = None,
    sector: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Dict[str, str]]:
    subject_lower = (subject or "").strip().lower()
    default = [
        {
            "question": "Quelle est la formule de l'aire d'un cercle ?",
            "choices": ["A: pi * r^2", "B: 2 * pi * r", "C: pi * d", "D: r^2"],
            "correct_answer": "A",
            "explanation": "L'aire d'un cercle est pi fois le rayon au carré.",
        },
        {
            "question": "Quel est le résultat de 12 + 8 ?",
            "choices": ["A: 18", "B: 20", "C: 24", "D: 19"],
            "correct_answer": "B",
            "explanation": "12 + 8 = 20.",
        },
    ]

    # Simple subject-specific templates
    banks = {
        "mathématiques": [
            {
                "question": "Quel est le résultat de 7 * 6 ?",
                "choices": ["A: 42", "B: 36", "C: 48", "D: 56"],
                "correct_answer": "A",
                "explanation": "7 multiplié par 6 égale 42.",
            },
            {
                "question": "Si x+3=8, quelle est la valeur de x ?",
                "choices": ["A: 4", "B: 5", "C: 6", "D: 3"],
                "correct_answer": "B",
                "explanation": "x = 8 - 3 = 5.",
            },
        ],
        "histoire": [
            {
                "question": "Quelle révolution a eu lieu en France en 1789 ?",
                "choices": ["A: Révolution française", "B: Révolution industrielle", "C: Révolution russe", "D: Révolution américaine"],
                "correct_answer": "A",
                "explanation": "La Révolution française a commencé en 1789.",
            },
            {
                "question": "Qui était le premier président des États-Unis ?",
                "choices": ["A: Abraham Lincoln", "B: George Washington", "C: Thomas Jefferson", "D: John Adams"],
                "correct_answer": "B",
                "explanation": "George Washington fut le premier président.",
            },
        ],
    }

    for key, qbank in banks.items():
        if key in subject_lower:
            return qbank[:num_questions]

    # fallback default
    out = []
    for i in range(min(num_questions, len(default))):
        out.append(default[i])
    # If still missing, repeat last choice with changed question index.
    while len(out) < num_questions:
        out.append({
            "question": f"Question de secours {len(out)+1} pour {subject or 'sujet'}.",
            "choices": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Question de secours générée automatiquement.",
        })
    return out
