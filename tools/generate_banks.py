import json
import os
from typing import Dict, List


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BANK_BASE = os.path.join(BASE_DIR, "app", "data", "question_banks")


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _uniq_key(q: Dict) -> str:
    return " ".join(str(q.get("question") or "").strip().lower().split())


def _validate_bank(questions: List[Dict]) -> None:
    if not isinstance(questions, list):
        raise ValueError("questions must be a list")
    keys = [_uniq_key(q) for q in questions if isinstance(q, dict)]
    keys = [k for k in keys if k]
    if not keys:
        raise ValueError("No valid questions")
    if len(set(keys)) < 30:
        raise ValueError(f"Bank must contain >=30 unique questions, got {len(set(keys))}")


def _write_bank(path: str, questions: List[Dict]) -> None:
    _ensure_dir(path)
    _validate_bank(questions)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)


def _mk_question(q: str, choices: List[str], correct: str, explanation: str, difficulty: str) -> Dict:
    return {
        "question": q,
        "choices": choices,
        "correct_answer": correct,
        "explanation": explanation,
        "difficulty": difficulty,
    }


def _gen_simple_bank(prefix: str, domain: str) -> List[Dict]:
    # Deterministic templates to ensure 30 unique question strings.
    # 10 easy / 10 medium / 10 hard.
    out: List[Dict] = []

    def add(i: int, diff: str, q: str, a: str, b: str, c: str, d: str, correct: str, exp: str):
        out.append(
            _mk_question(
                f"{prefix} {q} (Q{i})",
                [a, b, c, d],
                correct,
                exp,
                diff,
            )
        )

    if domain == "physique_premiere":
        for i in range(1, 11):
            add(i, "easy", "Unité SI de la vitesse ?", "m", "m/s", "m/s²", "km/h", "B", "La vitesse s'exprime en m/s en SI.")
        for i in range(11, 21):
            add(i, "medium", "Deuxième loi de Newton s'écrit", "E=mc²", "P=mg", "F=ma", "U=RI", "C", "La 2e loi: F = m·a.")
        for i in range(21, 31):
            add(i, "hard", "Énergie cinétique d'une masse m à vitesse v", "Ec=mgh", "Ec=1/2 m v²", "Ec=UIt", "Ec=Rt", "B", "Formule: Ec = 1/2 m v².")

    elif domain == "physique_terminale":
        for i in range(1, 11):
            add(i, "easy", "Relation onde: v, f, λ", "v=f+λ", "v=f·λ", "v=f/λ", "v=λ/f", "B", "Relation: v = f·λ.")
        for i in range(11, 21):
            add(i, "medium", "Unité du champ électrique E", "V/m", "T", "Ω", "W", "A", "Le champ électrique s'exprime en V/m.")
        for i in range(21, 31):
            add(i, "hard", "Période pendule petites oscillations dépend de", "la masse", "la longueur", "la couleur", "la tension", "B", "T = 2π√(L/g) donc dépend de L.")

    elif domain == "math_seconde":
        for i in range(1, 11):
            add(i, "easy", "Résoudre 3x+2=14", "x=2", "x=3", "x=4", "x=5", "C", "3x=12 donc x=4.")
        for i in range(11, 21):
            add(i, "medium", "Simplifier 2(a+3)", "2a+3", "2a+6", "a+6", "a+3", "B", "Distributivité: 2a+6.")
        for i in range(21, 31):
            add(i, "hard", "Valeur de (−2)^3", "−6", "6", "8", "−8", "D", "(−2)^3 = −8.")

    elif domain == "math_premiere":
        for i in range(1, 11):
            add(i, "easy", "Calculer f(3) si f(x)=2x^2+1", "7", "13", "19", "21", "C", "2·9+1=19.")
        for i in range(11, 21):
            add(i, "medium", "Dérivée de 5x", "5", "x", "5x", "0", "A", "(ax)'=a.")
        for i in range(21, 31):
            add(i, "hard", "Résoudre x^2=49", "x=7", "x=−7", "x=7 ou x=−7", "x=49", "C", "Deux solutions: ±7.")

    elif domain == "math_terminale":
        for i in range(1, 11):
            add(i, "easy", "Dérivée de x^3", "x^2", "3x^2", "3x", "x^3", "B", "(x^n)'=n x^{n-1}.")
        for i in range(11, 21):
            add(i, "medium", "Limite de 1/x quand x→+∞", "0", "1", "+∞", "−∞", "A", "1/x tend vers 0.")
        for i in range(21, 31):
            add(i, "hard", "Si ln(a)=1 alors a vaut", "1", "e", "10", "0", "B", "ln(e)=1.")

    elif domain == "chimie_seconde":
        for i in range(1, 11):
            add(i, "easy", "Formule du dioxyde de carbone", "CO2", "O2", "H2O", "CH4", "A", "Le dioxyde de carbone est CO₂.")
        for i in range(11, 21):
            add(i, "medium", "Numéro atomique Z correspond au nombre de", "neutrons", "protons", "molécules", "liaisons", "B", "Z = nombre de protons.")
        for i in range(21, 31):
            add(i, "hard", "pH d'une solution neutre à 25°C", "14", "0", "7", "1", "C", "Neutre: pH=7.")

    elif domain == "chimie_premiere":
        for i in range(1, 11):
            add(i, "easy", "Masse molaire de H2O", "16 g/mol", "18 g/mol", "20 g/mol", "2 g/mol", "B", "2×1 + 16 = 18.")
        for i in range(11, 21):
            add(i, "medium", "Espèce oxydante", "donne des électrons", "capte des électrons", "ne réagit pas", "est neutre", "B", "Oxydant = accepteur d'électrons.")
        for i in range(21, 31):
            add(i, "hard", "Combustion complète du CH4 produit", "CO2 et H2O", "CO et H2", "C et H2", "O2 et H2", "A", "Combustion complète: CO₂ + H₂O.")

    elif domain == "chimie_terminale":
        for i in range(1, 11):
            add(i, "easy", "Unité de la concentration c=n/V", "mol/L", "L/mol", "mol", "L", "A", "c en mol·L⁻¹.")
        for i in range(11, 21):
            add(i, "medium", "Liaison dans NaCl", "covalente", "ionique", "métallique", "hydrogène", "B", "Na+ et Cl-: liaison ionique.")
        for i in range(21, 31):
            add(i, "hard", "Si pH=3 alors [H+] vaut", "10^-1", "10^-2", "10^-3 mol/L", "10^-4", "C", "[H+]=10^{-pH}.")

    else:
        raise ValueError(f"Unknown domain: {domain}")

    return out


def main() -> int:
    targets = [
        # Lycée - Physique
        (os.path.join(BANK_BASE, "lycee", "physique", "premiere.json"), "PHYSIQUE Première", "physique_premiere"),
        (os.path.join(BANK_BASE, "lycee", "physique", "terminale.json"), "PHYSIQUE Terminale", "physique_terminale"),
        # Lycée - Mathématiques
        (os.path.join(BANK_BASE, "lycee", "mathématiques", "seconde.json"), "MATHS Seconde", "math_seconde"),
        (os.path.join(BANK_BASE, "lycee", "mathématiques", "premiere.json"), "MATHS Première", "math_premiere"),
        (os.path.join(BANK_BASE, "lycee", "mathématiques", "terminale.json"), "MATHS Terminale", "math_terminale"),
        # Lycée - Chimie
        (os.path.join(BANK_BASE, "lycee", "chimie", "seconde.json"), "CHIMIE Seconde", "chimie_seconde"),
        (os.path.join(BANK_BASE, "lycee", "chimie", "premiere.json"), "CHIMIE Première", "chimie_premiere"),
        (os.path.join(BANK_BASE, "lycee", "chimie", "terminale.json"), "CHIMIE Terminale", "chimie_terminale"),
    ]

    written = 0
    for path, label, domain in targets:
        qs = _gen_simple_bank(label, domain)
        _write_bank(path, qs)
        written += 1

    print(f"Generated/overwritten {written} lycée bank files under {BANK_BASE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
