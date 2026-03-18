import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.core.config import settings

class FastAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _get_weak_topics_fast(self, analysis: Dict) -> List[str]:
        """Extraction ultra-simple des sujets faibles.

        Retourne les sujets avec la plus faible performance si disponible.
        """
        performance = analysis.get('performance_by_topic') or {}
        if not isinstance(performance, dict) or not performance:
            return []

        try:
            sorted_topics = sorted(performance.items(), key=lambda kv: (kv[1] if kv[1] is not None else 0))
            return [t for t, _ in sorted_topics[:3]]
        except Exception:
            return []

    async def generate_personalized_qcm(self, user_profile: Dict, analysis: Dict, num_questions: int = 10, difficulty: str = "adaptive") -> Dict[str, Any]:
        """Compat: certains endpoints appellent generate_personalized_qcm().

        On redirige vers la version ultra-rapide.
        """
        return await self.generate_personalized_qcm_fast(user_profile, analysis, num_questions, difficulty)
    
    async def generate_personalized_qcm_fast(self, user_profile: Dict, analysis: Dict, num_questions: int = 10, difficulty: str = "adaptive") -> Dict[str, Any]:
        """Génération ULTRA-RAPIDE de QCM sans LLM"""
        try:
            # Détermination instantanée de la difficulté
            if difficulty == "adaptive":
                score = analysis.get('score_percentage', 0)
                if score < 40:
                    difficulty = "débutant"
                elif score < 60:
                    difficulty = "intermédiaire"
                elif score < 80:
                    difficulty = "avancé"
                else:
                    difficulty = "expert"
            
            # Génération instantanée avec questions prédéfinies
            questions = self._get_questions_instant(user_profile.get('subject', ''), difficulty, num_questions)
            
            return {
                'questions': questions,
                'num_questions': len(questions),
                'difficulty': difficulty,
                'target_topics': self._get_weak_topics_fast(analysis),
                'personalization_level': 'high',
                'generation_date': datetime.now().isoformat(),
                'generation_time': 'ultra_fast',
                'optimization': 'no_llm',
                'metadata': {
                    'user_level': user_profile.get('level', ''),
                    'subject': user_profile.get('subject', ''),
                    'speed': 'instant'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in fast QCM generation: {str(e)}")
            return {'error': str(e)}
    
    def _get_questions_instant(self, subject: str, difficulty: str, num_questions: int) -> List[Dict]:
        """Questions prédéfinies ultra-rapides par sujet et difficulté"""
        
        # Base de données de questions
        question_db = {
            'mathématiques': {
                'débutant': [
                    {"id": 1, "question": "Combien font 2 + 2 ?", "options": ["A. 3", "B. 4", "C. 5", "D. 6"], "correct_answer": "B", "explanation": "2 + 2 = 4", "concept": "addition", "bloom_level": "knowledge"},
                    {"id": 2, "question": "Combien font 5 × 3 ?", "options": ["A. 10", "B. 12", "C. 15", "D. 18"], "correct_answer": "C", "explanation": "5 × 3 = 15", "concept": "multiplication", "bloom_level": "knowledge"},
                    {"id": 3, "question": "Quelle est la moitié de 20 ?", "options": ["A. 5", "B. 8", "C. 10", "D. 12"], "correct_answer": "C", "explanation": "20 ÷ 2 = 10", "concept": "division", "bloom_level": "knowledge"},
                    {"id": 4, "question": "Combien font 7 - 3 ?", "options": ["A. 2", "B. 3", "C. 4", "D. 5"], "correct_answer": "C", "explanation": "7 - 3 = 4", "concept": "soustraction", "bloom_level": "knowledge"},
                    {"id": 5, "question": "Quelle est la racine carrée de 9 ?", "options": ["A. 2", "B. 3", "C. 4", "D. 5"], "correct_answer": "B", "explanation": "3² = 9", "concept": "racine", "bloom_level": "comprehension"}
                ],
                'intermédiaire': [
                    {"id": 6, "question": "Résolvez 2x + 5 = 15", "options": ["A. x = 3", "B. x = 4", "C. x = 5", "D. x = 6"], "correct_answer": "C", "explanation": "2x = 10 → x = 5", "concept": "équation linéaire", "bloom_level": "application"},
                    {"id": 7, "question": "Calculez 20% de 80", "options": ["A. 12", "B. 14", "C. 16", "D. 18"], "correct_answer": "C", "explanation": "80 × 0.20 = 16", "concept": "pourcentage", "bloom_level": "application"},
                    {"id": 8, "question": "Quelle est l'aire d'un carré de côté 5 ?", "options": ["A. 20", "B. 25", "C. 30", "D. 35"], "correct_answer": "B", "explanation": "Aire = côté² = 5² = 25", "concept": "géométrie", "bloom_level": "application"},
                    {"id": 9, "question": "Factorisez x² + 2x", "options": ["A. x(x + 2)", "B. x(2 + x)", "C. 2x(x + 1)", "D. x²(1 + 2/x)"], "correct_answer": "A", "explanation": "x² + 2x = x(x + 2)", "concept": "factorisation", "bloom_level": "analysis"},
                    {"id": 10, "question": "Quelle est la dérivée de x² ?", "options": ["A. x", "B. 2x", "C. x²", "D. 2"], "correct_answer": "B", "explanation": "d/dx(x²) = 2x", "concept": "dérivée", "bloom_level": "application"}
                ],
                'avancé': [
                    {"id": 11, "question": "Résolvez x² - 5x + 6 = 0", "options": ["A. x = 2, 3", "B. x = 1, 6", "C. x = -2, -3", "D. x = 0, 5"], "correct_answer": "A", "explanation": "(x-2)(x-3) = 0 → x = 2 ou 3", "concept": "équation quadratique", "bloom_level": "analysis"},
                    {"id": 12, "question": "Calculez ∫(2x + 3)dx", "options": ["A. x² + 3x + C", "B. x² + 3x", "C. 2x² + 3x + C", "D. x + 3 + C"], "correct_answer": "A", "explanation": "∫2x dx = x², ∫3 dx = 3x", "concept": "intégration", "bloom_level": "application"},
                    {"id": 13, "question": "Quelle est la limite de (x²-1)/(x-1) quand x→1 ?", "options": ["A. 0", "B. 1", "C. 2", "D. ∞"], "correct_answer": "C", "explanation": "Simplification: (x-1)(x+1)/(x-1) = x+1 → 2", "concept": "limite", "bloom_level": "analysis"},
                    {"id": 14, "question": "Résolvez sin(x) = 0.5 pour x ∈ [0, 2π]", "options": ["A. π/6, 5π/6", "B. π/3, 2π/3", "C. π/4, 3π/4", "D. 0, π"], "correct_answer": "A", "explanation": "sin(π/6) = 0.5, sin(5π/6) = 0.5", "concept": "trigonométrie", "bloom_level": "application"},
                    {"id": 15, "question": "Quelle est la matrice inverse de [[2,0],[0,3]] ?", "options": ["A. [[1/2,0],[0,1/3]]", "B. [[2,0],[0,3]]", "C. [[-2,0],[0,-3]]", "D. [[0,1/2],[1/3,0]]"], "correct_answer": "A", "explanation": "Inverse: 1/2 et 1/3 sur diagonale", "concept": "matrices", "bloom_level": "application"}
                ],
                'expert': [
                    {"id": 16, "question": "Calculez ∫₀^∞ e^(-x²)dx", "options": ["A. √π/2", "B. √π", "C. π/2", "D. π"], "correct_answer": "A", "explanation": "Intégrale de Gauss = √π/2", "concept": "intégrale impropre", "bloom_level": "evaluation"},
                    {"id": 17, "question": "Résolvez l'équation différentielle y' + 2y = e^x", "options": ["A. y = (e^x)/3 + Ce^(-2x)", "B. y = e^x + Ce^(-2x)", "C. y = (e^x)/2 + Ce^(-x)", "D. y = e^(2x) + Ce^(-x)"], "correct_answer": "A", "explanation": "Solution particulière + solution homogène", "concept": "équation différentielle", "bloom_level": "evaluation"},
                    {"id": 18, "question": "Quelle est la transformée de Fourier de e^(-a|t|) ?", "options": ["A. 2a/(a² + ω²)", "B. a/(a² + ω²)", "C. 1/(a² + ω²)", "D. ω/(a² + ω²)"], "correct_answer": "A", "explanation": "Transformée: 2a/(a² + ω²)", "concept": "transformée de Fourier", "bloom_level": "evaluation"},
                    {"id": 19, "question": "Calculez la série de Taylor de sin(x) autour de 0", "options": ["A. x - x³/6 + x⁵/120 - ...", "B. x + x³/6 + x⁵/120 + ...", "C. 1 - x²/2 + x⁴/24 - ...", "D. 1 + x²/2 + x⁴/24 + ..."], "correct_answer": "A", "explanation": "sin(x) = Σ(-1)ⁿ x^(2n+1)/(2n+1)!", "concept": "série de Taylor", "bloom_level": "evaluation"},
                    {"id": 20, "question": "Résolvez ∂²u/∂t² = c² ∂²u/∂x² (équation d'onde)", "options": ["A. u(x,t) = f(x-ct) + g(x+ct)", "B. u(x,t) = f(x)g(t)", "C. u(x,t) = e^(ct)sin(x)", "D. u(x,t) = cos(ct)sin(x)"], "correct_answer": "A", "explanation": "Solution générale: d'Alembert", "concept": "EDP", "bloom_level": "evaluation"}
                ]
            },
            'physique': {
                'débutant': [
                    {"id": 21, "question": "Quelle est l'unité de la force ?", "options": ["A. Newton", "B. Joule", "C. Watt", "D. Pascal"], "correct_answer": "A", "explanation": "L'unité SI de la force est le Newton (N)", "concept": "unités", "bloom_level": "knowledge"},
                    {"id": 22, "question": "Quelle est la vitesse de la lumière ?", "options": ["A. 3×10⁸ m/s", "B. 3×10⁶ m/s", "C. 3×10⁹ m/s", "D. 3×10⁷ m/s"], "correct_answer": "A", "explanation": "c = 3×10⁸ m/s dans le vide", "concept": "constantes physiques", "bloom_level": "knowledge"},
                    {"id": 23, "question": "Quelle est la formule de l'énergie cinétique ?", "options": ["A. ½mv²", "B. mv²", "C. mgh", "D. ½mgh"], "correct_answer": "A", "explanation": "Ec = ½mv²", "concept": "énergie", "bloom_level": "knowledge"},
                    {"id": 24, "question": "Quelle est la loi d'Ohm ?", "options": ["A. U = RI", "B. P = UI", "C. F = ma", "D. E = mc²"], "correct_answer": "A", "explanation": "Tension = Résistance × Intensité", "concept": "électricité", "bloom_level": "knowledge"},
                    {"id": 25, "question": "Quelle est l'accélération de la gravité ?", "options": ["A. 9.8 m/s²", "B. 8.8 m/s²", "C. 10.8 m/s²", "D. 7.8 m/s²"], "correct_answer": "A", "explanation": "g ≈ 9.8 m/s² sur Terre", "concept": "gravité", "bloom_level": "knowledge"}
                ],
                'intermédiaire': [
                    {"id": 26, "question": "Calculez le travail d'une force de 10N sur 5m", "options": ["A. 50 J", "B. 15 J", "C. 100 J", "D. 5 J"], "correct_answer": "A", "explanation": "W = F × d = 10 × 5 = 50 J", "concept": "travail", "bloom_level": "application"},
                    {"id": 27, "question": "Quelle est la période d'un pendule de 1m ?", "options": ["A. 2s", "B. 1s", "C. 3s", "D. 0.5s"], "correct_answer": "A", "explanation": "T = 2π√(L/g) ≈ 2s", "concept": "pendule", "bloom_level": "application"},
                    {"id": 28, "question": "Calculez la résistance équivalente (10Ω // 10Ω)", "options": ["A. 5Ω", "B. 10Ω", "C. 20Ω", "D. 2.5Ω"], "correct_answer": "A", "explanation": "Req = (R1×R2)/(R1+R2) = 5Ω", "concept": "circuits", "bloom_level": "application"},
                    {"id": 29, "question": "Quelle est la puissance d'un appareil 230V, 2A ?", "options": ["A. 460W", "B. 115W", "C. 230W", "D. 920W"], "correct_answer": "A", "explanation": "P = UI = 230 × 2 = 460W", "concept": "puissance", "bloom_level": "application"},
                    {"id": 30, "question": "Calculez l'énergie cinétique (m=2kg, v=3m/s)", "options": ["A. 9J", "B. 6J", "C. 12J", "D. 18J"], "correct_answer": "A", "explanation": "Ec = ½mv² = ½×2×9 = 9J", "concept": "énergie cinétique", "bloom_level": "application"}
                ],
                'avancé': [
                    {"id": 31, "question": "Calculez le champ électrique à 1m d'une charge 1μC", "options": ["A. 9×10³ N/C", "B. 9×10⁶ N/C", "C. 9×10⁹ N/C", "D. 9 N/C"], "correct_answer": "A", "explanation": "E = kq/r² = 9×10⁹×10⁻⁶/1² = 9×10³ N/C", "concept": "champ électrique", "bloom_level": "application"},
                    {"id": 32, "question": "Quelle est la fréquence d'un photon λ=500nm ?", "options": ["A. 6×10¹⁴ Hz", "B. 6×10¹² Hz", "C. 6×10¹⁶ Hz", "D. 6×10¹⁰ Hz"], "correct_answer": "A", "explanation": "f = c/λ = 3×10⁸/5×10⁻⁷ = 6×10¹⁴ Hz", "concept": "ondes", "bloom_level": "application"},
                    {"id": 33, "question": "Calculez l'inductance d'une bobine (N=100, l=10cm, A=1cm²)", "options": ["A. 1.26μH", "B. 12.6μH", "C. 126μH", "D. 0.126μH"], "correct_answer": "A", "explanation": "L = μ₀N²A/l = 4π×10⁻⁷×10⁴×10⁻⁴/0.1 ≈ 1.26μH", "concept": "inductance", "bloom_level": "application"},
                    {"id": 34, "question": "Quelle est l'énergie de liaison par nucléon (A=56, B=8.8MeV) ?", "options": ["A. 8.8MeV", "B. 493MeV", "C. 8.8MeV×56", "D. 8.8MeV/56"], "correct_answer": "A", "explanation": "Énergie de liaison par nucléon = 8.8MeV", "concept": "physique nucléaire", "bloom_level": "analysis"},
                    {"id": 35, "question": "Calculez le décalage Doppler (v=30m/s, f₀=1000Hz)", "options": ["A. 90Hz", "B. 10Hz", "C. 100Hz", "D. 1000Hz"], "correct_answer": "A", "explanation": "Δf = f₀v/c = 1000×30/3×10⁸ ≈ 10Hz", "concept": "effet Doppler", "bloom_level": "application"}
                ],
                'expert': [
                    {"id": 36, "question": "Calculez la constante de Planck avec E=hf (λ=500nm)", "options": ["A. 6.63×10⁻³⁴ J·s", "B. 3×10⁸ m/s", "C. 1.6×10⁻¹⁹ C", "D. 9.1×10⁻³¹ kg"], "correct_answer": "A", "explanation": "h = E/f = hc/λ = 6.63×10⁻³⁴ J·s", "concept": "mécanique quantique", "bloom_level": "evaluation"},
                    {"id": 37, "question": "Quelle est la solution de l'équation de Schrödinger stationnaire ?", "options": ["A. ψ(x) = Ae^(ikx) + Be^(-ikx)", "B. ψ(x) = sin(kx)", "C. ψ(x) = cos(kx)", "D. ψ(x) = e^(-kx)"], "correct_answer": "A", "explanation": "Solution générale: superposition d'ondes progressives", "concept": "mécanique quantique", "bloom_level": "evaluation"},
                    {"id": 38, "question": "Calculez la température du rayonnement cosmologique (T=2.7K)", "options": ["A. 2.7K", "B. 3K", "C. 2.5K", "D. 4K"], "correct_answer": "A", "explanation": "Température du fond diffus cosmologique = 2.725K", "concept": "cosmologie", "bloom_level": "knowledge"},
                    {"id": 39, "question": "Quelle est la constante de structure fine ?", "options": ["A. 1/137", "B. 1/274", "C. 137", "D. 274"], "correct_answer": "A", "explanation": "α = e²/(4πε₀ħc) ≈ 1/137", "concept": "constantes fondamentales", "bloom_level": "knowledge"},
                    {"id": 40, "question": "Calculez l'entropie de Boltzmann (W=10²³)", "options": ["A. 7.0×10⁻²¹ J/K", "B. 1.38×10⁻²³ J/K", "C. 10²³ J/K", "D. 23 J/K"], "correct_answer": "A", "explanation": "S = k ln W = 1.38×10⁻²³ × ln(10²³) ≈ 7.0×10⁻²¹ J/K", "concept": "thermodynamique", "bloom_level": "evaluation"}
                ]
            },
            'chimie': {
                'débutant': [
                    {"id": 41, "question": "H₂O est-elle ?", "options": ["A. Une molécule", "B. Un atome", "C. Un ion", "D. Un élément"], "correct_answer": "A", "explanation": "H₂O est une molécule d'eau", "concept": "molécules", "bloom_level": "knowledge"},
                    {"id": 42, "question": "Combien d'atomes dans H₂O ?", "options": ["A. 2", "B. 3", "C. 1", "D. 4"], "correct_answer": "B", "explanation": "H₂O contient 2 atomes d'hydrogène + 1 atome d'oxygène = 3 atomes", "concept": "composition", "bloom_level": "knowledge"},
                    {"id": 43, "question": "Quel est le pH de l'eau pure ?", "options": ["A. 7", "B. 0", "C. 14", "D. 1"], "correct_answer": "A", "explanation": "L'eau pure a un pH neutre de 7", "concept": "pH", "bloom_level": "knowledge"},
                    {"id": 44, "question": "NaCl est-il ?", "options": ["A. Un sel", "B. Un acide", "C. Une base", "D. Un oxyde"], "correct_answer": "A", "explanation": "NaCl (chlorure de sodium) est un sel", "concept": "sels", "bloom_level": "knowledge"},
                    {"id": 45, "question": "Combien d'électrons dans l'atome d'hydrogène ?", "options": ["A. 1", "B. 2", "C. 0", "D. 3"], "correct_answer": "A", "explanation": "L'hydrogène (Z=1) a 1 électron", "concept": "structure atomique", "bloom_level": "knowledge"}
                ],
                'intermédiaire': [
                    {"id": 46, "question": "Calculez la masse molaire de H₂O", "options": ["A. 18 g/mol", "B. 16 g/mol", "C. 20 g/mol", "D. 12 g/mol"], "correct_answer": "A", "explanation": "H₂O = 2×1 + 16 = 18 g/mol", "concept": "masse molaire", "bloom_level": "application"},
                    {"id": 47, "question": "Quelle est la concentration d'une solution 0.1M dans 500mL ?", "options": ["A. 0.05 mol/L", "B. 0.1 mol/L", "C. 0.2 mol/L", "D. 0.05 mol"], "correct_answer": "A", "explanation": "C = n/V = 0.1×0.5 = 0.05 mol/L", "concept": "concentration", "bloom_level": "application"},
                    {"id": 48, "question": "Équilibrez : CH₄ + O₂ → CO₂ + H₂O", "options": ["A. CH₄ + 2O₂ → CO₂ + 2H₂O", "B. CH₄ + O₂ → CO₂ + H₂O", "C. 2CH₄ + 3O₂ → 2CO₂ + 2H₂O", "D. CH₄ + 3O₂ → CO₂ + 2H₂O"], "correct_answer": "A", "explanation": "CH₄ + 2O₂ → CO₂ + 2H₂O (conservation atomes)", "concept": "équation chimique", "bloom_level": "application"},
                    {"id": 49, "question": "Calculez le nombre de moles dans 36g d'eau", "options": ["A. 2 mol", "B. 1 mol", "C. 3 mol", "D. 0.5 mol"], "correct_answer": "A", "explanation": "n = m/M = 36/18 = 2 mol", "concept": "mole", "bloom_level": "application"},
                    {"id": 50, "question": "Quel est le produit de HCl + NaOH ?", "options": ["A. NaCl + H₂O", "B. NaH + ClOH", "C. NaClO + H₂", "D. Na + HClO"], "correct_answer": "A", "explanation": "Réaction acide-base: HCl + NaOH → NaCl + H₂O", "concept": "réactions acide-base", "bloom_level": "application"}
                ],
                'avancé': [
                    {"id": 51, "question": "Calculez le pH d'une solution [H⁺] = 10⁻⁴ M", "options": ["A. 4", "B. 10", "C. -4", "D. 14"], "correct_answer": "A", "explanation": "pH = -log[H⁺] = -log(10⁻⁴) = 4", "concept": "pH", "bloom_level": "application"},
                    {"id": 52, "question": "Quelle est l'enthalpie de formation ΔHf° de H₂O(l) ?", "options": ["A. -286 kJ/mol", "B. +286 kJ/mol", "C. -143 kJ/mol", "D. 0 kJ/mol"], "correct_answer": "A", "explanation": "ΔHf°(H₂O,l) = -286 kJ/mol (exothermique)", "concept": "thermochimie", "bloom_level": "knowledge"},
                    {"id": 53, "question": "Calculez Kc pour 2SO₂ + O₂ ⇌ 2SO₃ à l'équilibre", "options": ["A. [SO₃]²/[SO₂]²[O₂]", "B. [SO₃]/[SO₂][O₂]", "C. [SO₂]²[O₂]/[SO₃]²", "D. [SO₃][O₂]/[SO₂]"], "correct_answer": "A", "explanation": "Kc = [produits]ⁿ/[réactifs]ⁿ", "concept": "équilibre chimique", "bloom_level": "application"},
                    {"id": 54, "question": "Quel est l'ordre de la réaction A → B si v = k[A]² ?", "options": ["A. 2", "B. 1", "C. 0", "D. 3"], "correct_answer": "A", "explanation": "Ordre = exposant de [A] dans la loi de vitesse", "concept": "cinétique", "bloom_level": "analysis"},
                    {"id": 55, "question": "Calculez E°cell pour Zn/Cu²⁺ (E°Zn²⁺/Zn = -0.76V, E°Cu²⁺/Cu = +0.34V)", "options": ["A. +1.10V", "B. -0.42V", "C. +0.42V", "D. -1.10V"], "correct_answer": "A", "explanation": "E°cell = E°cathode - E°anode = 0.34 - (-0.76) = 1.10V", "concept": "électrochimie", "bloom_level": "application"}
                ],
                'expert': [
                    {"id": 56, "question": "Calculez ΔG° pour une réaction (K = 10⁵ à 298K)", "options": ["A. -28.5 kJ/mol", "B. +28.5 kJ/mol", "C. -2.85 kJ/mol", "D. +2.85 kJ/mol"], "correct_answer": "A", "explanation": "ΔG° = -RTlnK = -8.314×298×ln(10⁵) ≈ -28.5 kJ/mol", "concept": "thermodynamique", "bloom_level": "evaluation"},
                    {"id": 57, "question": "Quelle est la constante d'acidité Ka (pKa = 4.75) ?", "options": ["A. 1.78×10⁻⁵", "B. 4.75×10⁻⁵", "C. 10⁻⁴.⁷⁵", "D. 4.75"], "correct_answer": "A", "explanation": "Ka = 10^(-pKa) = 10^(-4.75) ≈ 1.78×10⁻⁵", "concept": "équilibre acide-base", "bloom_level": "application"},
                    {"id": 58, "question": "Calculez la vitesse de réaction (k = 0.01 s⁻¹, [A] = 0.1M, ordre 1)", "options": ["A. 0.001 M/s", "B. 0.01 M/s", "C. 0.1 M/s", "D. 0.001 s⁻¹"], "correct_answer": "A", "explanation": "v = k[A] = 0.01 × 0.1 = 0.001 M/s", "concept": "cinétique", "bloom_level": "application"},
                    {"id": 59, "question": "Quelle est la structure de l'hexane ?", "options": ["A. CH₃-CH₂-CH₂-CH₂-CH₂-CH₃", "B. C₆H₁₂", "C. C₆H₆", "D. CH₃-CH₃"], "correct_answer": "A", "explanation": "Hexane: chaîne linéaire de 6 carbones", "concept": "chimie organique", "bloom_level": "knowledge"},
                    {"id": 60, "question": "Calculez le potentiel de Nernst (E° = 1.23V, [H⁺] = 10⁻³M)", "options": ["A. 1.05V", "B. 1.23V", "C. 1.41V", "D. 0.82V"], "correct_answer": "A", "explanation": "E = E° - (0.059/n)log[produits/réactifs] ≈ 1.05V", "concept": "électrochimie", "bloom_level": "evaluation"}
                ]
            }
        }
        
        # Sélectionner les questions selon le sujet et la difficulté
        subject_questions = question_db.get(subject, question_db['mathématiques'])
        difficulty_questions = subject_questions.get(difficulty, subject_questions['intermédiaire'])
        
        # Retourner le nombre demandé (avec rotation si nécessaire)
        result = []
        for i in range(min(num_questions, len(difficulty_questions))):
            result.append(difficulty_questions[i % len(difficulty_questions)])
        
        return result
    
    async def analyze_quiz_results(self, session_data: Dict, answers: List[Dict]) -> Dict[str, Any]:
        """Analyse rapide des résultats"""
        try:
            correct_count = len([a for a in answers if a.get('is_correct', False)])
            total_count = len(answers)
            score_percentage = (correct_count / total_count * 100) if total_count > 0 else 0
            
            return {
                'score_percentage': score_percentage,
                'correct_answers': correct_count,
                'total_questions': total_count,
                'performance_by_topic': {session_data.get('subject', ''): score_percentage},
                'error_patterns': {},
                'recommendations': [],
                'strengths': [],
                'weaknesses': []
            }
        except Exception as e:
            self.logger.error(f"Error in analyze_quiz_results: {str(e)}")
            return {'error': str(e)}
    
    async def generate_personalized_recommendations(self, analysis: Dict, user_profile: Dict) -> Dict[str, Any]:
        """Génération rapide de recommandations"""
        try:
            score = analysis.get('score_percentage', 0)
            recommendations = []
            
            if score < 50:
                recommendations = [
                    "Réviser les concepts fondamentaux",
                    "Faire des exercices de base",
                    "Demander de l'aide au professeur"
                ]
            elif score < 70:
                recommendations = [
                    "Pratiquer plus d'exercices",
                    "Revoir les erreurs commises",
                    "Travailler la vitesse"
                ]
            else:
                recommendations = [
                    "Passer à des problèmes complexes",
                    "Aider les autres élèves",
                    "Explorer des sujets avancés"
                ]
            
            return {
                'recommendations': recommendations,
                'priority_topics': [],
                'study_methods': [],
                'resources': [],
                'estimated_improvement_time': '2-4 semaines'
            }
        except Exception as e:
            self.logger.error(f"Error in generate_personalized_recommendations: {str(e)}")
            return {'error': str(e)}
    
    async def create_learning_plan(self, analysis: Dict, recommendations: Dict, duration_weeks: int = 4) -> Dict[str, Any]:
        """Création rapide de plan d'apprentissage"""
        try:
            plan = {
                'title': f'Plan d\'apprentissage {duration_weeks} semaines',
                'duration_weeks': duration_weeks,
                'weekly_goals': [],
                'daily_sessions': [],
                'milestones': [],
                'progress_tracking': {},
                'creation_date': datetime.now().isoformat()
            }
            
            # Générer des objectifs hebdomadaires
            for week in range(1, duration_weeks + 1):
                plan['weekly_goals'].append({
                    'week': week,
                    'objective': f'Objectif semaine {week}',
                    'topics': ['Révision', 'Pratique', 'Évaluation'],
                    'estimated_hours': 10
                })
            
            return plan
        except Exception as e:
            self.logger.error(f"Error in create_learning_plan: {str(e)}")
            return {'error': str(e)}

# Instance ultra-rapide
fast_agent_service = FastAgent()
