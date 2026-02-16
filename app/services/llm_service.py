import httpx
from typing import Dict, List, Any, Optional
from app.core.config import settings
from app.services.cache_service import cache_service
import json
import random
import time

class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL
        
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to Ollama API"""
        print(f"DEBUG: Making request to {self.base_url}{endpoint}")
        print(f"DEBUG: Payload: {payload}")
        print(f"DEBUG: Model: {self.model}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=180.0  # Augmenté à 180 secondes
                )
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response body: {response.text}")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"DEBUG: Error in _make_request: {type(e).__name__}: {str(e)}")
                print(f"DEBUG: Full error details: {repr(e)}")
                raise
    
    async def generate_quiz(
        self, 
        subject: str, 
        level: str, 
        num_questions: int = 10,
        topics: Optional[List[str]] = None,
        country: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions using LLM"""
        
        print(f"DEBUG: generate_quiz called with subject={subject}, level={level}, num_questions={num_questions}, country={country}")
        print(f"DEBUG: Target: Generate exactly {num_questions} questions")
        
        # Désactiver complètement le cache pour éviter les répétitions
        # if not force_refresh:
        #     cached_questions = cache_service.get_cached_quiz(subject, level, num_questions, topics)
        #     if cached_questions:
        #         return cached_questions
        
        topics_str = f" sur les thèmes: {', '.join(topics)}" if topics else ""
        country_str = f" pour le pays/région: {country}" if country else ""
        seed = int(time.time()) + random.randint(1, 1000)  # Add random variation
        
        # Définir les contraintes géographiques spécifiques
        geo_constraints = ""
        if country:
            country_lower = country.lower()
            if 'france' in country_lower:
                geo_constraints = (
                    "CONTEXTE OBLIGATOIRE FRANCE: "
                    "Génère EXCLUSIVEMENT des questions sur la France. "
                    "INTERDICTION FORMELLE de mentionner les États-Unis, l'Amérique, ou tout autre pays non-européen. "
                    "Pour l'histoire: concentre-toi sur l'histoire de France uniquement. "
                    "Pour la géographie: uniquement la géographie française. "
                    "Pour l'économie: uniquement l'économie française. "
                    "Pour la littérature: uniquement la littérature française. "
                    "Pour la politique: uniquement les institutions françaises. "
                )
            elif 'europe' in country_lower:
                geo_constraints = (
                    "CONTEXTE OBLIGATOIRE EUROPE: "
                    "Génère des questions sur l'Europe et les pays européens. "
                    "Évite les références américaines ou asiatiques sauf pour comparaison. "
                )
            elif ('amérique' in country_lower or 'america' in country_lower or 
                  'états-unis' in country_lower or 'usa' in country_lower):
                geo_constraints = (
                    "CONTEXTE OBLIGATOIRE AMÉRIQUE: "
                    "Génère des questions sur les États-Unis et l'Amérique. "
                    "Concentre-toi sur l'histoire, la géographie et la culture américaines. "
                )
            elif 'asie' in country_lower:
                geo_constraints = (
                    "CONTEXTE OBLIGATOIRE ASIE: "
                    "Génère des questions sur l'Asie et les pays asiatiques. "
                    "Concentre-toi sur l'histoire, la géographie et la culture asiatiques. "
                )
            elif 'afrique' in country_lower:
                geo_constraints = (
                    "CONTEXTE OBLIGATOIRE AFRIQUE: "
                    "Génère des questions sur l'Afrique et les pays africains. "
                    "Concentre-toi sur l'histoire, la géographie et la culture africaines. "
                )
            else:
                geo_constraints = f"CONTEXTE PAYS/RÉGION: {country}. "
        
        prompt = (
            f"Tu es un professeur expert qui crée des questions d'examen pour '{subject}' niveau {level}{country_str}{topics_str}. "
            f"Génère {num_questions} questions QCM uniques qui testent des compétences différentes: "
            "1. Questions de connaissance fondamentale (définitions, concepts clés) "
            "2. Questions d'application pratique (résolution de problèmes, cas concrets) "
            "3. Questions d'analyse/comparaison (avantages, inconvénients, différences) "
            "4. Questions de synthèse/évaluation (jugement, recommandation, choix optimal) "
            f"{geo_constraints}"
            "EXIGENCES CRITIQUES ANTI-RÉPÉTITION: "
            "- CHAQUE question doit aborder un aspect RADICALEMENT différent du sujet "
            "- VARIE les types de questions: définition, application, analyse, comparaison, évaluation "
            "- CHANGE les contextes: historique, contemporain, théorique, pratique "
            "- MODIFIE les structures: question directe, mise en situation, problème à résoudre "
            "- ÉVITE à tout prix les questions similaires ou les concepts qui se chevauchent "
            "- ASSURE-TOI que chaque question explore une nouvelle facette du sujet "
            "- UTILISE des verbes d'action variés: analyser, comparer, évaluer, expliquer, calculer "
            "- CRÉE des options de réponse uniques pour chaque question "
            "- VÉRIFIE qu'aucune question ne ressemble à une précédente "
            "Format JSON STRICT: "
            "[{\"question\":\"question complète avec contexte si nécessaire\",\"choices\":[\"option A\",\"option B\",\"option C\",\"option D\"],\"correct_answer\":\"texte exact de la bonne réponse\",\"explanation\":\"explication pédagogique concise\"}]"
        )
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.98,  # Maximum randomness
                "top_p": 0.99,
                "top_k": 50,
                "max_tokens": 1500,
                "num_predict": 1500,
                "num_ctx": 4096,
                "num_batch": 512,
                "num_gpu": 0,  # Forcer CPU
                "num_thread": 1,
                "seed": seed,
                "repeat_penalty": 1.5,  # Very strong repetition penalty
                "presence_penalty": 1.5,
                "frequency_penalty": 1.3,
                "tfs_z": 1.0,  # Tail free sampling
                "typical_p": 0.95  # Typical sampling
            }
        }
        
        try:
            print(f"DEBUG: Starting LLM request...")
            response = await self._make_request("/api/generate", payload)
            content = response.get("response", "")
            print(f"DEBUG: Response content length: {len(content)}")
            
            # Clean up the response - remove markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]   # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()
            
            # Extract JSON from response
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                print(f"DEBUG: Extracted JSON: {json_str[:200]}...")
                
                # Mapper les clés courtes vers les clés complètes
                questions = []
                parsed_questions = json.loads(json_str)
                
                # Vérifier si c'est une liste simple ou une liste d'objets
                if isinstance(parsed_questions, list) and len(parsed_questions) > 0:
                    if isinstance(parsed_questions[0], str):
                        # C'est une liste simple de choix, créer une question simple
                        questions.append({
                            "question": f"Question sur {subject} niveau {level}",
                            "choices": parsed_questions[:4],  # Prendre les 4 premiers
                            "correct_answer": parsed_questions[0] if len(parsed_questions) > 0 else "A",
                            "explanation": "Explication générée automatiquement"
                        })
                    else:
                        # C'est une liste d'objets questions
                        unique_questions = []
                        seen_concepts = set()
                        
                        for q in parsed_questions:
                            ch = q.get("c", q.get("choices", [])) or []
                            if isinstance(ch, list):
                                random.shuffle(ch)
                            
                            question_text = q.get("q", q.get("question", ""))
                            
                            # Vérifier l'unicité du concept
                            concept_key = question_text.lower()[:50]  # Premier 50 caractères comme clé de concept
                            if concept_key not in seen_concepts:
                                seen_concepts.add(concept_key)
                                unique_questions.append({
                                    "question": question_text,
                                    "choices": ch,
                                    "correct_answer": q.get("a", q.get("correct_answer", "")),
                                    "explanation": q.get("e", q.get("explanation", ""))
                                })
                        
                        logging.info(f"LLM returned {len(parsed_questions)} questions, {len(unique_questions)} unique after deduplication")
                        questions = unique_questions[:num_questions]  # Limiter au nombre demandé
                
                random.shuffle(questions)
                print(f"DEBUG: Parsed {len(questions)} unique questions (shuffled)")
                
                # Vérification finale de la diversité
                if len(questions) >= 2:
                    # Vérifier que les questions sont suffisamment différentes
                    question_starts = [q["question"][:30].lower() for q in questions]
                    duplicates = len(question_starts) - len(set(question_starts))
                    if duplicates > 0:
                        print(f"DEBUG: Found {duplicates} similar questions, regenerating...")
                        # Si trop de similarités, générer des fallback
                        return self._generate_fallback_questions(subject, level, num_questions)
                
                # S'assurer d'avoir le nombre exact de questions demandé
                if len(questions) < num_questions:
                    print(f"DEBUG: Only {len(questions)} questions generated, need {num_questions}. Adding unique generated questions...")
                    fallback_questions = self._generate_fallback_questions(subject, level, num_questions - len(questions))
                    questions.extend(fallback_questions)
                
                # Limiter au nombre exact demandé
                questions = questions[:num_questions]
                
                print(f"DEBUG: Generated {len(questions)} questions (requested: {num_questions})")
                
                # Mettre en cache le résultat (inclut topics) sauf si force_refresh
                if not force_refresh:
                    cache_service.cache_quiz(subject, level, num_questions, questions, topics)
                
                return questions
            else:
                print(f"DEBUG: No JSON found in response. Content: {content[:500]}...")
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"DEBUG: Failed to generate quiz: {type(e).__name__}: {str(e)}")
            print(f"DEBUG: Using fallback questions generation")
            
            # Fallback: générer des questions par défaut
            return self._generate_fallback_questions(subject, level, num_questions)
    
    def _generate_fallback_questions(self, subject: str, level: str, num_questions: int) -> List[Dict[str, Any]]:
        """Génère des questions d'examen par défaut quand le LLM n'est pas disponible"""
        print(f"DEBUG: Generating {num_questions} diverse fallback exam questions for {subject} {level}")
        
        questions = []
        
        # Questions d'examen par défaut selon le sujet avec plus de variété
        if subject.lower() in ['mathematiques', 'maths', 'math']:
            question_bank = [
                {
                    "question": "Une entreprise fabrique des pièces rectangulaires. Pour optimiser les coûts, elle doit minimiser le matériau utilisé tout en gardant une aire de 100 cm². Quelles dimensions (longueur × largeur) donnent le périmètre minimal ?",
                    "choices": ["10 cm × 10 cm", "20 cm × 5 cm", "25 cm × 4 cm", "50 cm × 2 cm"],
                    "correct_answer": "10 cm × 10 cm",
                    "explanation": "Pour une aire fixe, le carré minimise le périmètre. Avec 100 cm², le carré de 10×10 cm donne le périmètre le plus petit (40 cm)."
                },
                {
                    "question": "Un étudiant investit 2000€ à un taux d'intérêt composé de 4% par an. Après combien d'années son capital dépassera-t-il 2500€ ?",
                    "choices": ["4 ans", "5 ans", "6 ans", "7 ans"],
                    "correct_answer": "6 ans",
                    "explanation": "Formule: 2000×(1.04)^n > 2500. (1.04)^6 ≈ 1.265, donc 2000×1.265 ≈ 2530€ > 2500€."
                },
                {
                    "question": "Dans un triangle rectangle, l'hypoténuse mesure 13 cm et un côté mesure 5 cm. Quelle est l'aire du triangle ?",
                    "choices": ["30 cm²", "36 cm²", "42 cm²", "65 cm²"],
                    "correct_answer": "30 cm²",
                    "explanation": "Par Pythagore: autre côté = √(13²-5²) = √(169-25) = √144 = 12 cm. Aire = (5×12)/2 = 30 cm²."
                },
                {
                    "question": "Une fonction f(x) = 2x² - 8x + 6 représente le profit d'une entreprise. Pour quelle valeur de x le profit est-il maximal ?",
                    "choices": ["x = 1", "x = 2", "x = 3", "x = 4"],
                    "correct_answer": "x = 2",
                    "explanation": "Le maximum d'une parabole ax²+bx+c est atteint à x = -b/2a. Ici: x = -(-8)/(2×2) = 8/4 = 2."
                },
                {
                    "question": "Un réservoir cylindrique a un volume de 1000π litres. Si sa hauteur est de 10 mètres, quel est son rayon ?",
                    "choices": ["5 mètres", "10 mètres", "15 mètres", "20 mètres"],
                    "correct_answer": "10 mètres",
                    "explanation": "Volume = πr²h. Donc 1000π = πr²×10, donc r² = 100, donc r = 10 mètres."
                },
                {
                    "question": "Calculez la dérivée de f(x) = 3x³ - 6x² + 4x - 2",
                    "choices": ["f'(x) = 9x² - 12x + 4", "f'(x) = 9x² - 6x + 4", "f'(x) = 3x² - 12x + 4", "f'(x) = 6x² - 12x + 4"],
                    "correct_answer": "f'(x) = 9x² - 12x + 4",
                    "explanation": "Dérivée: (3x³)' = 9x², (-6x²)' = -12x, (4x)' = 4, (-2)' = 0. Donc f'(x) = 9x² - 12x + 4."
                },
                {
                    "question": "Résolvez l'équation différentielle dy/dx = 2x avec la condition initiale y(0) = 3",
                    "choices": ["y = x² + 3", "y = 2x + 3", "y = x² + 2x + 3", "y = 2x² + 3"],
                    "correct_answer": "y = x² + 3",
                    "explanation": "Intégration: dy = 2x dx → ∫dy = ∫2x dx → y = x² + C. Avec y(0) = 3: 3 = 0 + C → C = 3. Donc y = x² + 3."
                },
                {
                    "question": "Une usine produit 1000 unités par jour avec un coût fixe de 5000€ et un coût variable de 2€ par unité. Quel est le coût total pour produire 500 unités ?",
                    "choices": ["6000€", "7000€", "8000€", "9000€"],
                    "correct_answer": "6000€",
                    "explanation": "Coût total = coût fixe + (coût variable × quantité) = 5000 + (2 × 500) = 5000 + 1000 = 6000€."
                },
                {
                    "question": "Dans une série statistique, la moyenne est 25 et l'écart-type est 5. Quelle valeur se situe à 2 écarts-types au-dessus de la moyenne ?",
                    "choices": ["30", "35", "40", "45"],
                    "correct_answer": "35",
                    "explanation": "2 écarts-types au-dessus de la moyenne = 25 + (2 × 5) = 25 + 10 = 35."
                },
                {
                    "question": "Une matrice 2×2 a pour déterminant 12. Si un élément diagonal est 4, quel est l'autre élément diagonal ?",
                    "choices": ["3", "4", "6", "8"],
                    "correct_answer": "3",
                    "explanation": "Déterminant = a × d - b × c. Pour matrice diagonale: a × d = 12. Si a = 4, alors d = 12/4 = 3."
                }
            ]
        elif subject.lower() in ['histoire', 'history']:
            question_bank = [
                {
                    "question": "La Révolution française a profondément transformé la société française. Quelle institution de l'Ancien Régime a été abolie le 4 août 1789 ?",
                    "choices": ["La monarchie absolue", "Les privilèges féodaux et la dîme", "L'Église catholique", "Le parlement de Paris"],
                    "correct_answer": "Les privilèges féodaux et la dîme",
                    "explanation": "Dans la nuit du 4 août 1789, l'Assemblée nationale constituante a aboli les privilèges féodaux et la dîme, mettant fin au système féodal."
                },
                {
                    "question": "Napoléon Bonaparte a réorganisé l'administration française. Quel code juridique promulgué en 1804 a influencé de nombreux pays ?",
                    "choices": ["Code de commerce", "Code civil", "Code pénal", "Code administratif"],
                    "correct_answer": "Code civil",
                    "explanation": "Le Code civil des Français (1804), aussi appelé Code Napoléon, a unifié le droit privé et servi de modèle à de nombreux pays européens."
                },
                {
                    "question": "La IIIe République (1870-1940) a été marquée par quelles lois fondamentales qui ont consolidé le régime républicain ?",
                    "choices": ["Les lois de séparation de l'Église et de l'État", "Les lois constitutionnelles de 1875", "Le suffrage universel masculin", "La loi sur la liberté de la presse"],
                    "correct_answer": "Les lois constitutionnelles de 1875",
                    "explanation": "Les lois constitutionnelles de 1875 ont établi les bases institutionnelles de la IIIe République avec un Parlement bicaméral et un Président aux pouvoirs limités."
                },
                {
                    "question": "Pendant la Seconde Guerre mondiale, quel régime a collaboré avec l'Allemagne nazie de 1940 à 1944 ?",
                    "choices": ["La République française", "Le Gouvernement provisoire", "L'État français (régime de Vichy)", "La IVe République"],
                    "correct_answer": "L'État français (régime de Vichy)",
                    "explanation": "L'État français, dirigé par Philippe Pétain et installé à Vichy, a collaboré avec l'Allemagne nazie de 1940 à 1944."
                },
                {
                    "question": "Mai 1968 représente un tournant majeur dans la société française. Quel mouvement social a caractérisé cette période ?",
                    "choices": ["Grève générale étudiante et ouvrière", "Révolution militaire", "Crise économique mondiale", "Réforme constitutionnelle"],
                    "correct_answer": "Grève générale étudiante et ouvrière",
                    "explanation": "Mai 1968 a été marqué par une massive grève générale qui a paralysé la France, partant des mouvements étudiants et s'étendant au monde ouvrier."
                },
                {
                    "question": "La construction européenne a connu plusieurs étapes importantes. Quel traité a marqué la création de la Communauté Économique Européenne (CEE) en 1957 ?",
                    "choices": ["Traité de Paris", "Traité de Rome", "Traité de Maastricht", "Traité de Lisbonne"],
                    "correct_answer": "Traité de Rome",
                    "explanation": "Le Traité de Rome, signé le 25 mars 1957, a créé la Communauté Économique Européenne (CEE) et Euratom, fondant les bases de l'Union européenne actuelle."
                },
                {
                    "question": "Quel événement a déclenché la Première Guerre mondiale en 1914 ?",
                    "choices": ["L'assassinat de l'archiduc François-Ferdinand", "L'invasion de la Belgique", "La bataille de la Marne", "Le traité de Versailles"],
                    "correct_answer": "L'assassinat de l'archiduc François-Ferdinand",
                    "explanation": "L'assassinat de l'archiduc François-Ferdinand d'Autriche à Sarajevo le 28 juin 1914 a déclenché une crise diplomatique menant à la Première Guerre mondiale."
                },
                {
                    "question": "La Guerre Froide a opposé principalement deux blocs. Quels étaient les deux superpuissances ?",
                    "choices": ["États-Unis et Union Soviétique", "France et Allemagne", "Royaume-Uni et Italie", "Chine et Japon"],
                    "correct_answer": "États-Unis et Union Soviétique",
                    "explanation": "La Guerre Froide (1947-1991) a opposé le bloc occidental mené par les États-Unis et le bloc communiste mené par l'Union Soviétique."
                },
                {
                    "question": "Quel roi français a été exécuté pendant la Révolution française ?",
                    "choices": ["Louis XVI", "Louis XIV", "Louis XV", "Louis XVIII"],
                    "correct_answer": "Louis XVI",
                    "explanation": "Louis XVI a été guillotiné le 21 janvier 1793 à Paris, marquant la fin de la monarchie constitutionnelle."
                },
                {
                    "question": "La décolonisation française après 1945 a concerné de nombreux territoires. Quel pays a obtenu son indépendance en 1962 après une longue guerre ?",
                    "choices": ["Algérie", "Maroc", "Tunisie", "Vietnam"],
                    "correct_answer": "Algérie",
                    "explanation": "L'Algérie a obtenu son indépendance le 5 juillet 1962 après la guerre d'Algérie (1954-1962)."
                }
            ]
        elif subject.lower() in ['francais', 'français', 'french']:
            question_bank = [
                {
                    "question": "Dans le cadre professionnel, vous devez rédiger un email de plainte formelle. Quelle approche stylistique garantit le maximum d'efficacité ?",
                    "choices": ["Ton factuel et professionnel avec références précises", "Langage familier pour créer l'empathie", "Style poétique pour marquer les esprits", "Vocabulaire complexe pour montrer son expertise"],
                    "correct_answer": "Ton factuel et professionnel avec références précises",
                    "explanation": "Une communication professionnelle efficace requiert des faits vérifiables, un ton neutre et des références claires pour soutenir la réclamation."
                },
                {
                    "question": "Quelle figure de style est utilisée dans cette phrase publicitaire: 'Ce téléphone est une porte ouverte sur le monde' ?",
                    "choices": ["Métaphore", "Métonymie", "Hyperbole", "Personnification"],
                    "correct_answer": "Métaphore",
                    "explanation": "Comparaison implicite entre le téléphone et une porte sans utiliser 'comme' ou 'pareil à'."
                },
                {
                    "question": "Dans 'Les Misérables' de Victor Hugo, quel personnage incarne le plus la lutte entre justice et miséricorde ?",
                    "choices": ["Jean Valjean", "Javert", "Cosette", "Marius"],
                    "correct_answer": "Jean Valjean",
                    "explanation": "Jean Valjean représente le conflit central entre la loi (représentée par Javert) et la miséricorde chrétienne, illustrant la rédemption possible."
                },
                {
                    "question": "Quel temps verbal est utilisé dans cette phrase: 'Demain, nous aurons terminé le projet' ?",
                    "choices": ["Futur antérieur", "Futur simple", "Futur proche", "Conditionnel passé"],
                    "correct_answer": "Futur antérieur",
                    "explanation": "Le futur antérieur exprime une action future antérieure à une autre action future. Formation: futur simple de l'auxiliaire + participe passé."
                },
                {
                    "question": "En grammaire française, quelle fonction grammaticale remplit le pronom 'y' dans la phrase: 'J'y vais souvent' ?",
                    "choices": ["Complément de lieu", "Sujet", "Complément d'objet indirect", "Attribut du sujet"],
                    "correct_answer": "Complément de lieu",
                    "explanation": "Le pronom 'y' remplace généralement un complément de lieu introduit par 'à' ou un complément circonstanciel de lieu."
                },
                {
                    "question": "Quel mouvement littéraire du 19ème siècle est associé à des auteurs comme Balzac, Stendhal et Flaubert ?",
                    "choices": ["Le Romantisme", "Le Réalisme", "Le Symbolisme", "Le Naturalisme"],
                    "correct_answer": "Le Réalisme",
                    "explanation": "Le Réalisme, mouvement du 19ème siècle, cherche à représenter la réalité telle qu'elle est, sans idéalisation. Balzac, Stendhal et Flaubert en sont des représentants majeurs."
                },
                {
                    "question": "Dans un texte argumentatif, quel élément renforce le plus la crédibilité de l'auteur ?",
                    "choices": ["Des statistiques et des sources fiables", "Un style personnel et original", "Des opinions personnelles fortes", "Des exemples personnels uniquement"],
                    "correct_answer": "Des statistiques et des sources fiables",
                    "explanation": "Les données chiffrées et les sources vérifiables donnent un fondement objectif à l'argumentation et renforcent la crédibilité."
                },
                {
                    "question": "Quelle est la fonction principale du discours épique dans la littérature ?",
                    "choices": ["Célébrer les exploits d'un héros", "Critiquer la société", "Exprimer des sentiments personnels", "Décrire la nature"],
                    "correct_answer": "Célébrer les exploits d'un héros",
                    "explanation": "Le discours épique vise à glorifier les actions héroïques et les valeurs d'une communauté à travers des récits de exploits exceptionnels."
                },
                {
                    "question": "En analyse littéraire, que signifie l'expression 'marquer le texte' ?",
                    "choices": ["Ajouter des annotations et des notes de lecture", "Souligner les passages importants", "Réécrire le texte dans un autre style", "Traduire le texte dans une autre langue"],
                    "correct_answer": "Ajouter des annotations et des notes de lecture",
                    "explanation": "Marquer un texte consiste à y ajouter des commentaires, des notes marginales ou des surlignements pour en faciliter l'étude et l'analyse."
                },
                {
                    "question": "Quel procédé stylistique consiste à répéter un mot ou un groupe de mots en début de phrases successives ?",
                    "choices": ["L'anaphore", "L'épiphore", "Le chiasme", "La litote"],
                    "correct_answer": "L'anaphore",
                    "explanation": "L'anaphore est la répétition d'un même mot ou groupe de mots au début de plusieurs phrases ou vers successifs pour créer un effet de rythme et d'insistance."
                }
            ]
        else:
            # Questions génériques mais professionnelles
            question_bank = [
                {
                    "question": f"Dans un contexte professionnel, quelle approche est recommandée pour résoudre un problème complexe en {subject} ?",
                    "choices": [
                        "Analyser systématiquement les causes racines avant d'agir",
                        "Appliquer rapidement la première solution trouvée",
                        "Consulter uniquement les manuels théoriques",
                        "Éviter de documenter le processus pour gagner du temps"
                    ],
                    "correct_answer": "Analyser systématiquement les causes racines avant d'agir",
                    "explanation": "Une approche méthodique permet d'identifier les causes profondes et d'éviter les solutions superficielles qui ne résolvent pas le problème durablement."
                },
                {
                    "question": f"Quelle compétence est la plus critique pour un professionnel spécialisé en {subject} au niveau {level} ?",
                    "choices": [
                        "Capacité d'adaptation face aux nouvelles technologies",
                        "Mémorisation parfaite des théories fondamentales",
                        "Maîtrise exclusive des logiciels de base",
                        "Spécialisation dans un seul domaine technique"
                    ],
                    "correct_answer": "Capacité d'adaptation face aux nouvelles technologies",
                    "explanation": "Dans un monde en évolution rapide, la capacité d'apprendre et de s'adapter aux nouveaux outils et méthodes est essentielle pour rester compétitif."
                },
                {
                    "question": f"Comment évalueriez-vous l'efficacité d'une méthode dans le domaine de {subject} ?",
                    "choices": [
                        "Par sa capacité à résoudre des problèmes réels",
                        "Par sa complexité théorique",
                        "Par son ancienneté dans le domaine",
                        "Par le nombre de livres écrits à son sujet"
                    ],
                    "correct_answer": "Par sa capacité à résoudre des problèmes réels",
                    "explanation": "L'efficacité d'une méthode se mesure principalement par sa pertinence pratique et sa capacité à produire des résultats concrets."
                },
                {
                    "question": f"Quels sont les principaux défis actuels dans le domaine de {subject} ?",
                    "choices": [
                        "Intégration des nouvelles technologies",
                        "Adaptation aux changements réglementaires",
                        "Gestion des ressources limitées",
                        "Tous les éléments ci-dessus"
                    ],
                    "correct_answer": "Tous les éléments ci-dessus",
                    "explanation": "Les défis contemporains sont généralement multifactoriels, combinant aspects technologiques, réglementaires et économiques."
                },
                {
                    "question": f"Quelle méthode d'apprentissage est la plus efficace pour maîtriser {subject} ?",
                    "choices": [
                        "Pratique régulière avec feedback immédiat",
                        "Lecture passive de manuels",
                        "Mémorisation sans application",
                        "Apprentissage théorique uniquement"
                    ],
                    "correct_answer": "Pratique régulière avec feedback immédiat",
                    "explanation": "L'apprentissage par la pratique avec correction des erreurs permet une meilleure rétention et compréhension."
                },
                {
                    "question": f"Comment maintenir ses compétences à jour dans le domaine de {subject} ?",
                    "choices": [
                        "Formation continue et veille technologique",
                        "S'appuyer sur les connaissances acquises initialement",
                        "Changer de domaine périodiquement",
                        "Se spécialiser dans une seule technique"
                    ],
                    "correct_answer": "Formation continue et veille technologique",
                    "explanation": "Les domaines professionnels évoluent rapidement, nécessitant une mise à jour constante des connaissances et compétences."
                },
                {
                    "question": f"Quel est l'impact de l'automatisation sur les métiers liés à {subject} ?",
                    "choices": [
                        "Transformation des rôles vers des tâches à plus haute valeur",
                        "Disparition complète de tous les emplois",
                        "Aucun changement significatif",
                        "Augmentation uniquement des salaires"
                    ],
                    "correct_answer": "Transformation des rôles vers des tâches à plus haute valeur",
                    "explanation": "L'automatisation tend à éliminer les tâches répétitives tout en créant de nouveaux rôles nécessitant compétences analytiques et créatives."
                },
                {
                    "question": f"Quelle approche de communication est la plus efficace en entreprise pour présenter des résultats en {subject} ?",
                    "choices": [
                        "Visualisation des données avec narration claire",
                        "Présentation technique détaillée",
                        "Discours académique formel",
                        "Communication informelle seulement"
                    ],
                    "correct_answer": "Visualisation des données avec narration claire",
                    "explanation": "Les données visuelles combinées à une histoire cohérente facilitent la compréhension et la prise de décision."
                }
            ]
        
        # Sélectionner des questions variées et uniques
        available_questions = []
        for i, q in enumerate(question_bank):
            available_questions.append((i, q))
        
        # Si on n'a pas assez de questions uniques, créer des questions uniques supplémentaires
        if len(available_questions) < num_questions:
            print(f"DEBUG: Only {len(available_questions)} unique questions in bank, creating {num_questions - len(available_questions)} new unique questions...")
            # Créer des questions uniques basées sur des contextes différents
            for i in range(num_questions - len(available_questions)):
                new_question = self._create_unique_question(subject, level, i)
                available_questions.append((len(question_bank) + i, new_question))
        
        # Sélection aléatoire parmi les questions disponibles
        selected_indices = random.sample(range(len(available_questions)), num_questions)
        for idx in selected_indices:
            original_idx, q = available_questions[idx]
            questions.append(q)
        
        print(f"DEBUG: Generated {len(questions)} unique questions from bank + generated")
        return questions
    
    def _create_unique_question(self, subject: str, level: str, index: int) -> Dict[str, Any]:
        """Crée une question unique basée sur le sujet et le niveau"""
        contexts = [
            ("contexte industriel", "application", "entreprise"),
            ("contexte académique", "recherche", "université"),
            ("contexte pratique", "mise en situation", "cas concret"),
            ("contexte théorique", "conceptuel", "fondamental"),
            ("contexte technologique", "innovation", "numérique"),
            ("contexte social", "impact", "société"),
            ("contexte économique", "marché", "business"),
            ("contexte environnemental", "durable", "écologie")
        ]
        
        question_types = [
            "Quelle est la relation entre X et Y dans {context}?",
            "Comment {action} affecte {element} dans {context}?",
            "Quel rôle joue {concept} dans {context}?",
            "Pourquoi {phenomene} est-il important dans {context}?",
            "Comment évaluer {critere} dans {context}?"
        ]
        
        context, action_type, domain = contexts[index % len(contexts)]
        question_template = random.choice(question_types)
        
        # Créer une question unique basée sur le sujet
        question_text = question_template.format(
            context=context,
            action=action_type,
            element=f"les principes de {subject}",
            concept=f"la théorie de {subject}",
            phenomene=f"l'application de {subject}",
            critere=f"l'efficacité en {subject}",
            domain=domain
        )
        
        # Générer des choix uniques
        base_choices = [
            f"Approche structurée dans {context}",
            f"Méthode intuitive dans {context}",
            f"Analyse quantitative dans {context}",
            f"Évaluation qualitative dans {context}"
        ]
        
        random.shuffle(base_choices)
        
        return {
            "question": question_text,
            "choices": base_choices,
            "correct_answer": base_choices[0],
            "explanation": f"Dans le {context} de {subject}, l'approche structurée est généralement la plus efficace pour garantir des résultats cohérents et reproductibles."
        }
    
    async def analyze_answer_confidence(
        self, 
        question: str, 
        answer: str, 
        declared_confidence: float,
        is_correct: bool
    ) -> Dict[str, Any]:
        """Analyze confidence vs performance using LLM"""
        
        confidence_desc = "très élevée" if declared_confidence > 0.8 else "élevée" if declared_confidence > 0.6 else "moyenne" if declared_confidence > 0.4 else "basse" if declared_confidence > 0.2 else "très basse"
        
        prompt = f"""
        Analyse la cohérence entre la confiance déclarée et la performance réelle:
        
        Question: {question}
        Réponse donnée: {answer}
        Confiance déclarée: {confidence_desc} ({declared_confidence:.1f}/1.0)
        Réponse correcte: {"Oui" if is_correct else "Non"}
        
        Fournis une analyse brève (2-3 phrases) sur:
        1. La cohérence entre confiance et performance
        2. Indicateurs possibles de biais cognitif (Dunning-Kruger ou syndrome de l'imposteur)
        3. Recommandation métacognitive
        
        Format JSON:
        {{
            "coherence_score": 0.8,
            "bias_indicators": ["surestimation" ou "sous-estimation" ou "accurate"],
            "metacognitive_feedback": "feedback text",
            "confidence_analysis": "detailed analysis"
        }}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "max_tokens": 500
            }
        }
        
        try:
            response = await self._make_request("/api/generate", payload)
            content = response.get("response", "")
            
            # Extract JSON from response
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                analysis = json.loads(json_str)
                return analysis
            else:
                # Fallback if JSON parsing fails
                return {
                    "coherence_score": 0.5,
                    "bias_indicators": ["uncertain"],
                    "metacognitive_feedback": content[:200],
                    "confidence_analysis": content
                }
                
        except Exception as e:
            raise Exception(f"Failed to analyze confidence: {str(e)}")
    
    async def generate_cognitive_recommendations(
        self, 
        profile_data: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized recommendations based on cognitive profile"""
        
        prompt = f"""
        Basé sur le profil cognitif suivant, génère 5 recommandations personnalisées:
        
        Profil: {json.dumps(profile_data, indent=2)}
        
        Fournis des recommandations concrètes pour:
        1. Améliorer la métacognition
        2. Renforcer les points faibles identifiés
        3. Valoriser les forces
        4. Stratégies d'étude adaptées
        5. Gestion de la confiance
        
        Format JSON:
        {{
            "recommendations": [
                "recommandation 1",
                "recommandation 2",
                "recommandation 3",
                "recommandation 4",
                "recommandation 5"
            ]
        }}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "max_tokens": 800
            }
        }
        
        try:
            response = await self._make_request("/api/generate", payload)
            content = response.get("response", "")
            
            # Extract JSON from response
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                result = json.loads(json_str)
                return result.get("recommendations", [])
            else:
                return ["Améliorer l'autoévaluation", "Pratiquer la réflexion métacognitive"]
                
        except Exception as e:
            raise Exception(f"Failed to generate recommendations: {str(e)}")

# Global instance
llm_service = LLMService()
