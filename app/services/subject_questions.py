import random
import time
import os
import json

def normalize_subject(subject):
    """Normalise le nom du sujet pour la comparaison"""
    subject = subject.lower().strip()
    
    # Mapping des variations possibles
    subject_mapping = {
        'math': 'mathématiques',
        'maths': 'mathématiques',
        'mathematiques': 'mathématiques',
        'mathématiques': 'mathématiques',
        'physique': 'physique',
        'physics': 'physique',
        'chimie': 'chimie',
        'chemistry': 'chimie',
        'biologie': 'biologie',
        'biology': 'biologie',
        'histoire': 'histoire',
        'history': 'histoire',
        'geographie': 'géographie',
        'geography': 'géographie',
        'français': 'français',
        'french': 'français',
        'anglais': 'anglais',
        'english': 'anglais'
    }
    
    return subject_mapping.get(subject, subject)

def _norm_token(x):
    if x is None:
        return None
    v = str(x).strip().lower()
    # Normalize common variants (e.g. without accents)
    if v == "lycee":
        return "lycée"
    if v == "université":
        return "universite"
    return v


def _load_json_bank(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        qs = data.get("questions") if isinstance(data, dict) else None
        if not isinstance(qs, list):
            return []
        out = []
        for q in qs:
            if not isinstance(q, dict):
                continue
            # normalize minimal shape
            out.append({
                "question": q.get("question"),
                "choices": q.get("choices"),
                "correct_answer": q.get("correct_answer"),
                "explanation": q.get("explanation"),
                "difficulty": q.get("difficulty"),
            })
        return out
    except Exception:
        return []


def _uniq_by_text(questions):
    seen = set()
    out = []
    for q in questions or []:
        if not isinstance(q, dict):
            continue
        t = str(q.get("question") or "").strip().lower()
        t = " ".join(t.split())
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(q)
    return out


def _bank_path(subject_norm: str, lvl: str, cls: str, sec: str):
    base = os.path.join(os.path.dirname(__file__), "..", "data", "question_banks")
    base = os.path.abspath(base)

    if lvl == "lycée":
        if not cls:
            return None
        # app/data/question_banks/lycee/<subject>/<class_level>.json
        return os.path.join(base, "lycee", subject_norm, f"{cls}.json")

    if lvl == "universite":
        if not cls:
            return None
        # app/data/question_banks/universite/<subject>/<class_level>.json
        return os.path.join(base, "universite", subject_norm, f"{cls}.json")

    if lvl == "professionnel":
        if not sec:
            return None
        # app/data/question_banks/pro/<sector>/<subject>.json
        return os.path.join(base, "pro", sec, f"{subject_norm}.json")

    return None


def generate_questions_by_subject(
    subject: str,
    level: str,
    num_questions: int = 10,
    class_level: str = None,
    sector: str = None,
    difficulty: str = None,
):
    """Génère des questions QCM en fonction du sujet demandé.

    Mode strict: la banque locale est sélectionnée par (subject, level, class_level, sector, difficulty)
    afin d'éviter tout mélange entre classes/années/secteurs.
    """

    normalized_subject = normalize_subject(subject)
    lvl = _norm_token(level)
    cls = _norm_token(class_level)
    sec = _norm_token(sector)
    diff = _norm_token(difficulty)

    # Prefer JSON banks when present (keeps the code small and allows large banks).
    json_path = _bank_path(normalized_subject, lvl, cls, sec)
    if json_path and os.path.exists(json_path):
        pool_all = _load_json_bank(json_path)
        pool_all = _uniq_by_text(pool_all)
        if len(pool_all) < 1:
            raise ValueError("Banque locale indisponible pour cette combinaison")

        bucket = diff if diff in {"easy", "medium", "hard"} else None
        if bucket:
            # 1) On essaie la difficulté demandée
            pool = [q for q in pool_all if _norm_token(q.get("difficulty")) == bucket]
            pool = _uniq_by_text(pool)
            # 2) Si pas assez de questions pour cette difficulté, on élargit
            #    à toutes les difficultés de la banque, en gardant zéro répétition.
            if len(pool) < num_questions:
                pool = pool_all
        else:
            pool = pool_all

        random.seed(f"{normalized_subject}|{lvl}|{cls}|{sec}|{diff}|{time.time_ns()}")
        # STRICT: jamais moins que demandé et jamais de doublon.
        if len(pool) < num_questions:
            raise ValueError("Banque locale insuffisante: impossible de garantir zéro répétition.")
        return random.sample(pool, num_questions)

    # Seed includes the strict key so 2 profils différents ne piochent pas dans la même banque.
    random.seed(f"{normalized_subject}|{lvl}|{cls}|{sec}|{diff}|{time.time_ns()}")

    questions = []

    def _pick(pool, n):
        pool = list(pool or [])
        if not pool:
            return []
        if len(pool) < n:
            raise ValueError("Banque locale insuffisante: impossible de garantir zéro répétition.")
        return random.sample(pool, n)

    # ----------------------------
    # BANKS PROFESSIONNELLES
    # ----------------------------
    # In mode professionnel, on ne mélange pas avec les matières scolaires.
    if lvl == "professionnel" and sec:
        # Banques courtes (exemples) : à enrichir.
        banks_pro = {
            "informatique_data": {
                "easy": [
                    {
                        "question": "En Python, quel type représente une collection ordonnée et modifiable ?",
                        "choices": ["tuple", "list", "set", "dict"],
                        "correct_answer": "B",
                        "explanation": "Une list est ordonnée et modifiable."
                    },
                    {
                        "question": "Quel mot-clé Python permet de gérer les exceptions ?",
                        "choices": ["catch", "try/except", "guard", "error"],
                        "correct_answer": "B",
                        "explanation": "En Python, on utilise try/except."
                    },
                    {
                        "question": "Quel type Python est immuable ?",
                        "choices": ["list", "dict", "set", "tuple"],
                        "correct_answer": "D",
                        "explanation": "Les tuples sont immuables."
                    },
                    {
                        "question": "Quel est le résultat de len({'a':1,'b':2}) ?",
                        "choices": ["1", "2", "3", "Erreur"],
                        "correct_answer": "B",
                        "explanation": "Le dictionnaire contient 2 clés."
                    },
                    {
                        "question": "Quel module standard Python sert à manipuler le JSON ?",
                        "choices": ["csv", "json", "pickle", "xml"],
                        "correct_answer": "B",
                        "explanation": "Le module json permet d’encoder/décoder du JSON."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la complexité moyenne d'une recherche par clé dans un dictionnaire Python (dict) ?",
                        "choices": ["O(1)", "O(log n)", "O(n)", "O(n log n)"],
                        "correct_answer": "A",
                        "explanation": "En moyenne, l'accès par hash est O(1)."
                    },
                    {
                        "question": "Dans une API REST, quel verbe HTTP est le plus adapté pour créer une ressource ?",
                        "choices": ["GET", "POST", "PUT", "DELETE"],
                        "correct_answer": "B",
                        "explanation": "POST sert typiquement à créer une ressource."
                    },
                    {
                        "question": "Quel mécanisme évite l’exécution bloquante en Python async ?",
                        "choices": ["thread.sleep", "await", "global", "lambda"],
                        "correct_answer": "B",
                        "explanation": "await permet de libérer la boucle d’événements."
                    },
                    {
                        "question": "Quel format est le plus courant pour sérialiser des données entre frontend et backend ?",
                        "choices": ["INI", "JSON", "BMP", "EXE"],
                        "correct_answer": "B",
                        "explanation": "JSON est le standard le plus répandu pour APIs web."
                    },
                    {
                        "question": "En base SQL, quelle commande récupère des lignes ?",
                        "choices": ["SELECT", "INSERT", "UPDATE", "DROP"],
                        "correct_answer": "A",
                        "explanation": "SELECT permet de lire des données."
                    },
                    {
                        "question": "Quel code HTTP indique une requête invalide côté client ?",
                        "choices": ["200", "201", "400", "500"],
                        "correct_answer": "C",
                        "explanation": "400 = Bad Request."
                    },
                ],
                "hard": [
                    {
                        "question": "Quel composant assure l'idempotence dans un pipeline de données (ex: ETL) ?",
                        "choices": ["Des requêtes SELECT", "Des clés de déduplication", "Le cache navigateur", "Le CSS"],
                        "correct_answer": "B",
                        "explanation": "La déduplication par clé permet de rejouer sans dupliquer."
                    },
                    {
                        "question": "Quelle approche réduit le risque de conditions de concurrence lors d’écritures concurrentes ?",
                        "choices": ["Supprimer les index", "Transactions + contraintes", "Changer la couleur du UI", "Augmenter la taille des images"],
                        "correct_answer": "B",
                        "explanation": "Transactions/contraintes protègent l’intégrité."
                    },
                    {
                        "question": "Quel concept décrit le fait de pouvoir relancer un job sans doubler les effets ?",
                        "choices": ["Idempotence", "Polymorphisme", "Compression", "Routage"],
                        "correct_answer": "A",
                        "explanation": "Idempotence = mêmes effets même si relancé."
                    },
                    {
                        "question": "Quel outil garantit la reproductibilité des dépendances Python ?",
                        "choices": ["requirements.txt verrouillé", "README", "favicon", "HTML"],
                        "correct_answer": "A",
                        "explanation": "Un fichier de dépendances fixe aide à reproduire l’environnement."
                    },
                    {
                        "question": "Quel problème survient si on ouvre une transaction et on oublie de commit/rollback ?",
                        "choices": ["Aucun", "Locks / blocages possibles", "Meilleure performance", "Compression automatique"],
                        "correct_answer": "B",
                        "explanation": "Des verrous peuvent rester actifs et bloquer."
                    },
                ],
            },
            "business_finance": {
                "easy": [
                    {
                        "question": "Qu'est-ce qu'une marge brute ?",
                        "choices": ["CA - coût des ventes", "Résultat net + impôts", "Trésorerie - dettes", "Actifs - passifs"],
                        "correct_answer": "A",
                        "explanation": "Marge brute = chiffre d'affaires - coût des ventes."
                    },
                ],
                "medium": [
                    {
                        "question": "Quel indicateur mesure la rentabilité d'un investissement ?",
                        "choices": ["ROI", "TVA", "PIB", "CP"],
                        "correct_answer": "A",
                        "explanation": "Le ROI (Return On Investment) mesure la rentabilité."
                    },
                ],
                "hard": [
                    {
                        "question": "Dans une analyse de risque, quel concept relie rendement espéré et volatilité ?",
                        "choices": ["Pareto", "Markowitz", "Bayes", "Fibonacci"],
                        "correct_answer": "B",
                        "explanation": "Le modèle de Markowitz (frontière efficiente) relie rendement/risque."
                    },
                ],
            },
            "sante": {
                "easy": [
                    {
                        "question": "Quel paramètre est un signe vital ?",
                        "choices": ["Température", "Couleur des yeux", "Taille des chaussures", "Groupe sanguin"],
                        "correct_answer": "A",
                        "explanation": "La température fait partie des signes vitaux."
                    },
                ],
                "medium": [
                    {
                        "question": "Quel organe est principalement responsable des échanges gazeux ?",
                        "choices": ["Foie", "Poumons", "Reins", "Pancréas"],
                        "correct_answer": "B",
                        "explanation": "Les poumons assurent les échanges O2/CO2."
                    },
                ],
                "hard": [
                    {
                        "question": "Quel type d'étude est le plus adapté pour estimer une incidence ?",
                        "choices": ["Cas-témoins", "Cohorte", "Série de cas", "Étude qualitative"],
                        "correct_answer": "B",
                        "explanation": "Une cohorte permet d'estimer l'incidence."
                    },
                ],
            },
        }

        bank = banks_pro.get(sec, {})
        bucket = diff if diff in {"easy", "medium", "hard"} else "medium"
        pool = bank.get(bucket, [])
        if not pool:
            raise ValueError("Banque de questions indisponible pour ce secteur/difficulté")
        return _pick(pool, num_questions)
    
    # ----------------------------
    # BANKS SCOLAIRES/UNIVERSITAIRES
    # ----------------------------
    # En mode strict, on exige class_level pour lycée/université.
    if lvl in {"lycée", "universite"} and not cls:
        raise ValueError("class_level requis pour ce niveau")

    bucket = diff if diff in {"easy", "medium", "hard"} else "medium"

    # Questions de MATHÉMATIQUES
    if normalized_subject == 'mathématiques':
        banks_math = {
            # Lycée
            "seconde": {
                "easy": [
                    {
                        "question": "Résolvez l'équation 2x + 7 = 15. Quelle est la valeur de x ?",
                        "choices": ["x = 2", "x = 3", "x = 4", "x = 5"],
                        "correct_answer": "C",
                        "explanation": "2x + 7 = 15 → 2x = 8 → x = 4"
                    },
                    {
                        "question": "Dans une classe de 30 élèves, 18 ont réussi un test. Quel est le pourcentage de réussite ?",
                        "choices": ["50%", "60%", "70%", "80%"],
                        "correct_answer": "B",
                        "explanation": "Pourcentage = (18/30) × 100 = 60%"
                    },
                ],
                "medium": [
                    {
                        "question": "Factorisez l'expression x² - 9.",
                        "choices": ["(x-3)(x+3)", "(x-9)(x+1)", "(x-3)²", "(x+3)(x-3)"],
                        "correct_answer": "A",
                        "explanation": "Différence de carrés : x² - 9 = (x-3)(x+3)."
                    },
                ],
                "hard": [
                    {
                        "question": "Un triangle rectangle a des côtés de 3 cm et 4 cm. Quelle est la longueur de l'hypoténuse ?",
                        "choices": ["5 cm", "6 cm", "7 cm", "8 cm"],
                        "correct_answer": "A",
                        "explanation": "Pythagore : c² = 3² + 4² = 25 → c = 5."
                    },
                ],
            },
            "premiere": {
                "easy": [
                    {
                        "question": "Si f(x) = 3x² - 2x + 5, calculez f(2).",
                        "choices": ["13", "15", "17", "19"],
                        "correct_answer": "A",
                        "explanation": "f(2) = 12 - 4 + 5 = 13."
                    },
                ],
                "medium": [
                    {
                        "question": "Résolvez le système : x + y = 10 et x - y = 4.",
                        "choices": ["x = 7, y = 3", "x = 6, y = 4", "x = 8, y = 2", "x = 5, y = 5"],
                        "correct_answer": "A",
                        "explanation": "Addition : 2x = 14 → x = 7 puis y = 3."
                    },
                ],
                "hard": [
                    {
                        "question": "Calculez l'aire d'un cercle de rayon 6 cm.",
                        "choices": ["36π cm²", "12π cm²", "24π cm²", "18π cm²"],
                        "correct_answer": "A",
                        "explanation": "A = πr² = 36π."
                    },
                ],
            },
            "terminale": {
                "easy": [
                    {
                        "question": "Calculez la dérivée de f(x) = x³ + 2x² - 5x + 1.",
                        "choices": ["3x² + 4x - 5", "3x² + 2x - 5", "x² + 4x - 5", "3x² + 4x + 1"],
                        "correct_answer": "A",
                        "explanation": "f'(x) = 3x² + 4x - 5."
                    },
                ],
                "medium": [
                    {
                        "question": "Calculez la limite de f(x) = (x²-4)/(x-2) lorsque x tend vers 2.",
                        "choices": ["0", "1", "2", "4"],
                        "correct_answer": "D",
                        "explanation": "(x²-4)=(x-2)(x+2) donc limite = 4."
                    },
                ],
                "hard": [
                    {
                        "question": "La moyenne de 5 nombres est 12. Si quatre nombres sont 10, 11, 13 et 14, quel est le cinquième ?",
                        "choices": ["10", "11", "12", "13"],
                        "correct_answer": "C",
                        "explanation": "Somme=60, connus=48, reste=12."
                    },
                ],
            },
            # Université
            "l1": {
                "easy": [
                    {
                        "question": "Calculez la somme des entiers de 1 à n.",
                        "choices": ["n(n+1)", "n(n+1)/2", "(n+1)/2", "n²"],
                        "correct_answer": "B",
                        "explanation": "Somme = n(n+1)/2."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la dérivée de sin(x) ?",
                        "choices": ["sin(x)", "-sin(x)", "cos(x)", "-cos(x)"],
                        "correct_answer": "C",
                        "explanation": "d/dx sin(x) = cos(x)."
                    },
                ],
                "hard": [
                    {
                        "question": "Évaluez l'intégrale ∫0^1 x dx.",
                        "choices": ["1", "1/2", "2", "0"],
                        "correct_answer": "B",
                        "explanation": "∫0^1 x dx = [x²/2]_0^1 = 1/2."
                    },
                ],
            },
            "l2": {
                "easy": [
                    {
                        "question": "Une matrice A est inversible si et seulement si :",
                        "choices": ["det(A)=0", "det(A)≠0", "A est diagonale", "A est symétrique"],
                        "correct_answer": "B",
                        "explanation": "A inversible ⇔ det(A) ≠ 0."
                    },
                ],
                "medium": [
                    {
                        "question": "Si A est orthogonale, quelle relation est vraie ?",
                        "choices": ["A^T A = I", "A^2 = I", "A = 0", "det(A)=0"],
                        "correct_answer": "A",
                        "explanation": "Orthogonale ⇒ A^T A = I."
                    },
                ],
                "hard": [
                    {
                        "question": "Résolvez y' = y avec y(0)=1.",
                        "choices": ["y=x", "y=e^x", "y=1/x", "y=ln(x)"],
                        "correct_answer": "B",
                        "explanation": "Solution y = Ce^x, et y(0)=1 ⇒ C=1."
                    },
                ],
            },
            "l3": {
                "easy": [
                    {
                        "question": "Une série ∑ a_n converge absolument si :",
                        "choices": ["∑ a_n diverge", "∑ |a_n| converge", "a_n est constant", "a_n = 0"],
                        "correct_answer": "B",
                        "explanation": "Définition de la convergence absolue."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle transformation diagonalise une matrice symétrique réelle ?",
                        "choices": ["Orthogonale", "Affine", "Projective", "Aléatoire"],
                        "correct_answer": "A",
                        "explanation": "Théorème spectral : diagonalisation orthogonale."
                    },
                ],
                "hard": [
                    {
                        "question": "La convergence en loi d'une suite (X_n) vers X implique :",
                        "choices": ["convergence p.s.", "convergence en probabilité", "convergence des fonctions caractéristiques", "X_n=X"],
                        "correct_answer": "C",
                        "explanation": "Caractérisation par fonctions caractéristiques."
                    },
                ],
            },
            "m1": {
                "easy": [
                    {
                        "question": "Dans un espace de Hilbert, un opérateur auto-adjoint a des valeurs propres :",
                        "choices": ["complexes", "réelles", "négatives", "nulles"],
                        "correct_answer": "B",
                        "explanation": "Auto-adjoint ⇒ spectre réel."
                    },
                ],
                "medium": [
                    {
                        "question": "En optimisation convexe, une condition suffisante d'optimalité est :",
                        "choices": ["∇f(x*)=0", "f non continue", "x* au hasard", "∇f(x*)≠0"],
                        "correct_answer": "A",
                        "explanation": "Pour f convexe différentiable : ∇f(x*)=0."
                    },
                ],
                "hard": [
                    {
                        "question": "Quel est le dual de l'espace L^p (p>1) ?",
                        "choices": ["L^1", "L^∞", "L^q avec 1/p+1/q=1", "C([0,1])"],
                        "correct_answer": "C",
                        "explanation": "Dualité L^p/L^q."
                    },
                ],
            },
            "m2": {
                "easy": [
                    {
                        "question": "Un estimateur est sans biais si :",
                        "choices": ["E[θ̂]=θ", "Var(θ̂)=0", "θ̂ est constant", "E[θ̂]=0"],
                        "correct_answer": "A",
                        "explanation": "Définition sans biais."
                    },
                ],
                "medium": [
                    {
                        "question": "En ML, la régularisation L2 correspond à :",
                        "choices": ["|w|", "w²", "exp(w)", "aucune"],
                        "correct_answer": "B",
                        "explanation": "L2 pénalise la somme des carrés."
                    },
                ],
                "hard": [
                    {
                        "question": "Le théorème de Neyman-Pearson traite :",
                        "choices": ["régression", "tests d'hypothèses", "clustering", "PCA"],
                        "correct_answer": "B",
                        "explanation": "Fondements des tests optimaux."
                    },
                ],
            },
        }

        pool = (banks_math.get(cls) or {}).get(bucket, [])
        if not pool:
            raise ValueError("Banque de questions indisponible pour cette classe/année/difficulté")
        questions = _pick(pool, num_questions)
    
    # Questions de PHYSIQUE
    elif normalized_subject == 'physique':
        banks_phys = {
            "seconde": {
                "easy": [
                    {
                        "question": "Quelle est l'unité SI de l'énergie ?",
                        "choices": ["Joule (J)", "Newton (N)", "Watt (W)", "Pascal (Pa)"],
                        "correct_answer": "A",
                        "explanation": "L'unité SI de l'énergie est le Joule."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la loi d'Ohm ?",
                        "choices": ["U = R × I", "P = U × I", "E = m × c²", "F = m × a"],
                        "correct_answer": "A",
                        "explanation": "U = R × I."
                    },
                ],
                "hard": [
                    {
                        "question": "Un objet de masse 2 kg est soumis à une force de 10 N. Quelle est son accélération ?",
                        "choices": ["5 m/s²", "10 m/s²", "20 m/s²", "2 m/s²"],
                        "correct_answer": "A",
                        "explanation": "a=F/m=10/2=5."
                    },
                ],
            },
            "premiere": {
                "easy": [
                    {
                        "question": "Quelle est la vitesse de la lumière dans le vide ?",
                        "choices": ["299 792 458 m/s", "300 000 000 m/s", "285 000 000 m/s", "310 000 000 m/s"],
                        "correct_answer": "A",
                        "explanation": "c ≈ 3,0×10^8 m/s."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la formule de la deuxième loi de Newton ?",
                        "choices": ["F = ma", "E = mc²", "P = mg", "V = d/t"],
                        "correct_answer": "A",
                        "explanation": "F = m a."
                    },
                ],
                "hard": [
                    {
                        "question": "Un courant de 2 A circule dans une résistance de 10 Ω pendant 5 secondes. Quelle est l'énergie dissipée ?",
                        "choices": ["200 J", "100 J", "50 J", "400 J"],
                        "correct_answer": "A",
                        "explanation": "E=R I² t = 10×4×5=200."
                    },
                ],
            },
            "terminale": {
                "easy": [
                    {
                        "question": "Dans une onde électromagnétique, quel est le rapport entre la vitesse, la fréquence et la longueur d'onde ?",
                        "choices": ["v = f × λ", "v = f/λ", "v = λ/f", "v = f + λ"],
                        "correct_answer": "A",
                        "explanation": "v = fλ."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la période d'un pendule simple de longueur 1 m ? (g ≈ 9,81 m/s²)",
                        "choices": ["2,01 s", "1,00 s", "0,50 s", "3,14 s"],
                        "correct_answer": "A",
                        "explanation": "T=2π√(L/g)≈2,01 s."
                    },
                ],
                "hard": [
                    {
                        "question": "Quel est le principe fondamental de la thermodynamique qui énonce que l'énergie se conserve ?",
                        "choices": ["Premier principe", "Deuxième principe", "Troisième principe", "Principe zéro"],
                        "correct_answer": "A",
                        "explanation": "1er principe : conservation de l'énergie."
                    },
                ],
            },
        }

        pool = (banks_phys.get(cls) or {}).get(bucket, [])
        if not pool:
            raise ValueError("Banque de questions indisponible pour cette classe/année/difficulté")
        questions = _pick(pool, num_questions)
    
    # Questions de CHIMIE
    elif normalized_subject == 'chimie':
        banks_chem = {
            "seconde": {
                "easy": [
                    {
                        "question": "Quelle est la formule chimique de l'eau ?",
                        "choices": ["H₂O", "CO₂", "O₂", "H₂O₂"],
                        "correct_answer": "A",
                        "explanation": "H₂O."
                    },
                ],
                "medium": [
                    {
                        "question": "Quel est le numéro atomique du carbone ?",
                        "choices": ["6", "8", "12", "14"],
                        "correct_answer": "A",
                        "explanation": "Z(C)=6."
                    },
                ],
                "hard": [
                    {
                        "question": "Quel est le pH d'une solution neutre à 25°C ?",
                        "choices": ["7", "0", "14", "1"],
                        "correct_answer": "A",
                        "explanation": "pH=7."
                    },
                ],
            },
            "premiere": {
                "easy": [
                    {
                        "question": "Quelle est la réaction de combustion du méthane CH₄ ?",
                        "choices": ["CH₄ + 2O₂ → CO₂ + 2H₂O", "CH₄ + O₂ → CO + H₂O", "CH₄ + 2O₂ → CO + 2H₂O", "CH₄ + 3O₂ → CO₂ + 2H₂O"],
                        "correct_answer": "A",
                        "explanation": "Combustion complète : CO₂ et H₂O."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la masse molaire de NaCl ?",
                        "choices": ["58,44 g/mol", "39,34 g/mol", "74,44 g/mol", "35,45 g/mol"],
                        "correct_answer": "A",
                        "explanation": "22,99 + 35,45 = 58,44."
                    },
                ],
                "hard": [
                    {
                        "question": "Quel type de liaison relie les atomes dans une molécule d'eau ?",
                        "choices": ["Liaisons covalentes polaires", "Liaisons ioniques", "Liaisons métalliques", "Liaisons hydrogène"],
                        "correct_answer": "A",
                        "explanation": "Covalentes polaires O-H."
                    },
                ],
            },
            "terminale": {
                "easy": [
                    {
                        "question": "Quel gaz est produit par la réaction entre un acide et un carbonate ?",
                        "choices": ["CO₂", "H₂", "O₂", "N₂"],
                        "correct_answer": "A",
                        "explanation": "CO₂ est libéré."
                    },
                ],
                "medium": [
                    {
                        "question": "Quelle est la concentration en ions H⁺ d'une solution de pH 3 ?",
                        "choices": ["10⁻³ mol/L", "10⁻⁴ mol/L", "10⁻² mol/L", "10⁻¹ mol/L"],
                        "correct_answer": "A",
                        "explanation": "[H⁺]=10^-3."
                    },
                ],
                "hard": [
                    {
                        "question": "Quelle est la configuration électronique du néon (Z = 10) ?",
                        "choices": ["1s² 2s² 2p⁶", "1s² 2s² 2p⁴", "1s² 2s² 2p⁵", "1s² 2s² 2p⁷"],
                        "correct_answer": "A",
                        "explanation": "1s² 2s² 2p⁶."
                    },
                ],
            },
        }

        pool = (banks_chem.get(cls) or {}).get(bucket, [])
        if not pool:
            raise ValueError("Banque de questions indisponible pour cette classe/année/difficulté")
        questions = _pick(pool, num_questions)
    
    # Questions de BIOLOGIE
    elif normalized_subject == 'biologie':
        banks_bio = {
            "seconde": [
                {
                    "question": "Quel est le rôle principal des chloroplastes dans les cellules végétales ?",
                    "choices": ["Photosynthèse", "Respiration", "Division cellulaire", "Stockage d'énergie"],
                    "correct_answer": "A",
                    "explanation": "Les chloroplastes sont le site de la photosynthèse."
                },
                {
                    "question": "Quelle structure contrôle l'entrée et la sortie de substances dans la cellule ?",
                    "choices": ["Membrane cellulaire", "Paroi cellulaire", "Cytoplasme", "Noyau"],
                    "correct_answer": "A",
                    "explanation": "La membrane cellulaire régule les échanges."
                },
            ],
            "premiere": [
                {
                    "question": "Quel est le produit final de la glycolyse ?",
                    "choices": ["Pyruvate", "Glucose", "ATP", "CO₂"],
                    "correct_answer": "A",
                    "explanation": "La glycolyse produit du pyruvate."
                },
                {
                    "question": "Quel processus permet la formation des protéines ?",
                    "choices": ["Traduction", "Transcription", "Réplication", "Mitose"],
                    "correct_answer": "A",
                    "explanation": "La traduction synthétise les protéines à partir de l'ARNm."
                },
            ],
            "terminale": [
                {
                    "question": "Combien de paires de chromosomes possède un être humain normal ?",
                    "choices": ["23", "46", "22", "24"],
                    "correct_answer": "A",
                    "explanation": "23 paires (46 chromosomes)."
                },
                {
                    "question": "Quel type de cellule possède un vrai noyau ?",
                    "choices": ["Cellule eucaryote", "Cellule procaryote", "Cellule animale", "Cellule végétale"],
                    "correct_answer": "A",
                    "explanation": "Les cellules eucaryotes possèdent un noyau."
                },
            ],
        }

        pool = banks_bio.get(cls, [])
        if not pool:
            raise ValueError("Banque de questions indisponible pour cette classe/année")
        questions = _pick(pool, num_questions)
    
    # Questions d'HISTOIRE
    elif normalized_subject == 'histoire':
        banks_hist = {
            "seconde": [
                {
                    "question": "En quelle année a débuté la Révolution française ?",
                    "choices": ["1789", "1776", "1804", "1799"],
                    "correct_answer": "A",
                    "explanation": "1789."
                },
                {
                    "question": "Quelle était la capitale de l'Empire romain ?",
                    "choices": ["Rome", "Constantinople", "Athènes", "Alexandrie"],
                    "correct_answer": "A",
                    "explanation": "Rome."
                },
            ],
            "premiere": [
                {
                    "question": "En quelle année a débuté la Première Guerre mondiale ?",
                    "choices": ["1914", "1915", "1913", "1916"],
                    "correct_answer": "A",
                    "explanation": "1914."
                },
                {
                    "question": "En quelle année a eu lieu la chute du mur de Berlin ?",
                    "choices": ["1989", "1985", "1991", "1979"],
                    "correct_answer": "A",
                    "explanation": "1989."
                },
            ],
            "terminale": [
                {
                    "question": "En quelle année a été signée la Déclaration d'indépendance des États-Unis ?",
                    "choices": ["1776", "1775", "1777", "1783"],
                    "correct_answer": "A",
                    "explanation": "1776."
                },
                {
                    "question": "Quelle dynastie a construit la Grande Muraille de Chine (principalement) ?",
                    "choices": ["Dynastie Ming", "Dynastie Qin", "Dynastie Han", "Dynastie Tang"],
                    "correct_answer": "A",
                    "explanation": "Dynastie Ming."
                },
            ],
        }

        pool = banks_hist.get(cls, [])
        if not pool:
            raise ValueError("Banque de questions indisponible pour cette classe/année")
        questions = _pick(pool, num_questions)
    
    # Questions par défaut si sujet non reconnu
    else:
        raise ValueError("Banque de questions indisponible pour ce sujet.")
    
    return questions
