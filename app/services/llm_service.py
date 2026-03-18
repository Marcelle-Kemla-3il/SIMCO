import httpx
from typing import Dict, List, Any, Optional
from app.core.config import settings
from app.services.subject_questions import generate_questions_by_subject
import json
import re
import logging
import asyncio
import time
import random

class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL
        self._log = logging.getLogger(__name__)
        self._ollama_timeout_s = float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 20.0) or 20.0)

        # Similarity thresholds (word-level Jaccard). Applied for all subjects.
        self._max_allowed_similarity = 0.45

    def _extract_json_object(self, text: str) -> str:
        """Best-effort extraction of the first JSON object from a model output."""
        if not isinstance(text, str):
            raise ValueError("Non-string model output")
        t = text.strip()
        if t.startswith("{") and t.endswith("}"):
            return t
        m = re.search(r"\{[\s\S]*\}", t)
        if not m:
            raise ValueError("No JSON object found in model output")
        return m.group(0)

    def _coerce_correct_answer_to_letter(self, q: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure correct_answer is one of A-D.

        If correct_answer is a full text, map it to the matching choice.
        """
        if not isinstance(q, dict):
            return q

        choices = q.get("choices")
        if not isinstance(choices, list):
            return q

        correct = q.get("correct_answer")
        if isinstance(correct, str):
            c = correct.strip().upper()
            if c in {"A", "B", "C", "D"}:
                q["correct_answer"] = c
                return q

            # Try match by exact text
            for idx, ch in enumerate(choices[:4]):
                if isinstance(ch, str) and ch.strip() == correct.strip():
                    q["correct_answer"] = ["A", "B", "C", "D"][idx]
                    return q

        # Default: keep but sanitize to A (avoid crashes downstream)
        q["correct_answer"] = "A"
        return q

    def _questions_uniqueness_ratio(self, qs: List[Dict[str, Any]]) -> float:
        try:
            if not qs:
                return 0.0
            keys = []
            for q in qs:
                if not isinstance(q, dict):
                    continue
                t = self._normalize_question_signature(str(q.get("question") or ""))
                if t:
                    keys.append(t)
            if not keys:
                return 0.0
            return len(set(keys)) / float(len(keys))
        except Exception:
            return 0.0

    def _normalize_question_signature(self, text: str) -> str:
        """Normalize a question into a semantic-ish signature to catch templated repeats.

        - Lowercase
        - Remove trailing "(Q12)" style tokens
        - Replace numbers with '#'
        - Collapse whitespace
        - Keep word tokens only
        """
        try:
            t = str(text or "").strip().lower()
            # Remove templated suffixes like "(Q12)".
            t = re.sub(r"\(\s*q\s*\d+\s*\)$", "", t).strip()
            # Normalize common math function notations to reduce superficial differences.
            t = re.sub(r"f\s*\(\s*x\s*\)", "f(x)", t)
            # Replace digits (including decimals) with '#'
            t = re.sub(r"\d+(?:[\.,]\d+)?", "#", t)
            # Normalize common variable names
            t = re.sub(r"\b([xyz])\b", "var", t)
            # Keep only word characters and '#'
            t = re.sub(r"[^\w#]+", " ", t)
            t = re.sub(r"\s+", " ", t).strip()

            # Remove ultra-generic instruction words that make templates look different by just topic.
            stop = {
                "calculer",
                "calcule",
                "déterminer",
                "determiner",
                "résoudre",
                "resoudre",
                "trouver",
                "donner",
                "quelle",
                "quel",
                "quels",
                "quelles",
                "est",
                "sont",
                "dans",
                "si",
                "avec",
                "pour",
                "donnée",
                "donnee",
                "fonction",
            }
            parts = [p for p in t.split(" ") if p and p not in stop]
            return " ".join(parts)
        except Exception:
            return str(text or "").strip().lower()

    def _dedup_and_filter(self, qs: List[Dict[str, Any]], max_similarity: float) -> List[Dict[str, Any]]:
        """Deduplicate by normalized signature and reject overly similar questions."""
        out: List[Dict[str, Any]] = []
        seen = set()
        for q in qs or []:
            if not isinstance(q, dict):
                continue
            sig = self._normalize_question_signature(str(q.get("question") or ""))
            if not sig or sig in seen:
                continue
            # Similarity vs already accepted
            too_similar = False
            for prev in out:
                prev_sig = self._normalize_question_signature(str(prev.get("question") or ""))
                if self._jaccard_similarity(sig, prev_sig) > max_similarity:
                    too_similar = True
                    break
            if too_similar:
                continue
            seen.add(sig)
            out.append(q)
        return out

    def _dedup_only(self, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate only by normalized signature (no similarity rejection)."""
        out: List[Dict[str, Any]] = []
        seen = set()
        for q in qs or []:
            if not isinstance(q, dict):
                continue
            sig = self._normalize_question_signature(str(q.get("question") or ""))
            if not sig or sig in seen:
                continue
            seen.add(sig)
            out.append(q)
        return out

    def _jaccard_similarity(self, a: str, b: str) -> float:
        """Compute Jaccard similarity between two strings (word-level)."""
        try:
            words_a = set(re.findall(r"\b\w+\b", a.lower()))
            words_b = set(re.findall(r"\b\w+\b", b.lower()))
            if not words_a and not words_b:
                return 1.0
            if not words_a or not words_b:
                return 0.0
            inter = words_a & words_b
            union = words_a | words_b
            return len(inter) / len(union)
        except Exception:
            return 0.0

    def _max_similarity_in_batch(self, qs: List[Dict[str, Any]]) -> float:
        """Return the highest pairwise Jaccard similarity among questions."""
        try:
            texts = [str(q.get("question", "")).strip().lower() for q in qs if isinstance(q, dict)]
            max_sim = 0.0
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    sim = self._jaccard_similarity(texts[i], texts[j])
                    if sim > max_sim:
                        max_sim = sim
            return max_sim
        except Exception:
            return 0.0
        
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to Ollama API"""
        self._log.debug("Ollama request %s%s model=%s", self.base_url, endpoint, self.model)

        timeout = httpx.Timeout(self._ollama_timeout_s)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                )
                self._log.debug("Ollama response status=%s", response.status_code)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                self._log.warning("Ollama request failed: %s: %s", type(e).__name__, str(e))
                raise
    
    async def generate_quiz(
        self, 
        subject: str, 
        level: str, 
        num_questions: int = 10,
        topics: Optional[List[str]] = None,
        country: Optional[str] = None,
        force_refresh: bool = False,
        sector: Optional[str] = None,
        difficulty: Optional[str] = None,
        use_llm: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions.

        Prefers an Ollama LLM call when configured and use_llm=True.
        Falls back to the local question bank when LLM fails.
        """

        self._log.debug(
            "generate_quiz subject=%s level=%s num_questions=%s sector=%s difficulty=%s use_llm=%s",
            subject,
            level,
            num_questions,
            sector,
            difficulty,
            use_llm,
        )

        provider = str(getattr(settings, "LLM_PROVIDER", "")).strip().lower()

        if not use_llm or provider not in {"ollama", "mistral"}:
            provider = "local"

        self._log.info(
            "Quiz generation provider=%s subject=%s level=%s sector=%s difficulty=%s num_questions=%s",
            provider,
            subject,
            level,
            sector,
            difficulty,
            num_questions,
        )

        if use_llm and provider == "mistral" and getattr(settings, "MISTRAL_API_KEY", None):
            attempts = 3
            rounds = 6
            target_n = int(num_questions or 0)
            max_allowed_similarity = float(getattr(self, "_max_allowed_similarity", 0.45))
            last_err: Optional[Exception] = None

            collected: List[Dict[str, Any]] = []

            for round_idx in range(rounds):
                remaining = target_n - len(collected)
                if remaining <= 0:
                    break

                for attempt in range(attempts):
                    nonce = f"{int(time.time() * 1000)}-{random.randint(0, 1_000_000)}-r{round_idx}-a{attempt}"
                    try:
                        # Minimal Mistral Chat Completions call (OpenAI-compatible style)
                        # Note: users must set MISTRAL_API_KEY and MISTRAL_API_URL (optional).
                        base_url = str(getattr(settings, "MISTRAL_API_URL", "https://api.mistral.ai")).rstrip("/")
                        url = f"{base_url}/v1/chat/completions"

                        system = (
                            "Tu es un générateur de QCM. "
                            "Tu dois répondre STRICTEMENT en JSON valide, sans texte autour. "
                            "La réponse doit être un objet JSON avec exactement la clé 'questions' contenant une liste. "
                            "IMPORTANT: interdiction des questions templates/répétitives. "
                            "Chaque question doit tester un concept différent (sous-thème distinct). "
                            "Interdiction d'ajouter des suffixes comme '(Q12)' ou des numéros de question. "
                            "Interdiction de répéter le même type d'exercice (ex: 'Résoudre x^2=#', 'Calculer f(#)' etc.). "
                            "Varie les nombres, les expressions, et le contexte. "
                            "Les questions doivent être réellement différentes, pas des reformulations."
                        )
                        user_obj = {
                            "task": "generate_mcq",
                            "subject": subject,
                            "sector": sector,
                            "level": level,
                            "difficulty": difficulty,
                            "num_questions": remaining,
                            "format": {
                                "question": "string",
                                "choices": ["string", "string", "string", "string"],
                                "correct_answer": "A|B|C|D",
                                "explanation": "string",
                            },
                            "constraints": {
                                "choices_count": 4,
                                "language": "fr",
                                "no_markdown": True,
                                "no_repeated_questions": True,
                                "diversity": "high",
                                "max_similarity": max_allowed_similarity,
                                "nonce": nonce,
                            },
                        }

                        payload = {
                            "model": getattr(settings, "MISTRAL_MODEL", None) or "mistral-small-latest",
                            # Increase temperature slightly on retries to improve diversity.
                            "temperature": 0.4 + (0.2 * attempt) + (0.1 * round_idx),
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)},
                            ],
                        }

                        headers = {
                            "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                            "Content-Type": "application/json",
                        }

                        async with httpx.AsyncClient(timeout=60.0) as client:
                            r = await client.post(url, json=payload, headers=headers)
                            r.raise_for_status()
                            data = r.json()

                        content = None
                        try:
                            content = data.get("choices", [{}])[0].get("message", {}).get("content")
                        except Exception:
                            content = None

                        if not content:
                            raise ValueError("Empty Mistral response")

                        raw_json = self._extract_json_object(content)
                        parsed = json.loads(raw_json)
                        qs = parsed.get("questions") if isinstance(parsed, dict) else None
                        if not isinstance(qs, list):
                            raise ValueError("Invalid Mistral questions format")

                        formatted_questions: List[Dict[str, Any]] = []
                        for q in qs[: int(remaining)]:
                            if not isinstance(q, dict):
                                continue
                            q2 = {
                                "question": q.get("question"),
                                "choices": q.get("choices"),
                                "correct_answer": q.get("correct_answer"),
                                "explanation": q.get("explanation"),
                            }
                            q2 = self._coerce_correct_answer_to_letter(q2)
                            formatted_questions.append(q2)

                        filtered_new = self._dedup_and_filter(formatted_questions, max_similarity=max_allowed_similarity)
                        merged = self._dedup_and_filter(collected + filtered_new, max_similarity=max_allowed_similarity)
                        collected = merged

                        if len(collected) >= target_n:
                            return collected[:target_n]

                        # Success for this attempt (we got some new non-duplicate questions)
                        if len(filtered_new) > 0:
                            break
                    except Exception as e:
                        last_err = e
                        self._log.info("Mistral round %d attempt %d failed: %s: %s", round_idx + 1, attempt + 1, type(e).__name__, str(e))
                        try:
                            await asyncio.sleep(0.25)
                        except Exception:
                            pass

                # Tighten similarity slightly each round to reduce template repeats.
                max_allowed_similarity = max(0.30, max_allowed_similarity - 0.03)

            # If strict mode yields too few, progressively relax similarity to fill the batch.
            if len(collected) < target_n:
                relax_steps = [0.55, 0.65]
                for relax_sim in relax_steps:
                    if len(collected) >= target_n:
                        break
                    missing = target_n - len(collected)
                    for attempt in range(attempts):
                        nonce = f"{int(time.time() * 1000)}-{random.randint(0, 1_000_000)}-relax{int(relax_sim*100)}-{attempt}"
                        try:
                            base_url = str(getattr(settings, "MISTRAL_API_URL", "https://api.mistral.ai")).rstrip("/")
                            url = f"{base_url}/v1/chat/completions"

                            system = (
                                "Tu es un générateur de QCM. "
                                "Tu dois répondre STRICTEMENT en JSON valide, sans texte autour. "
                                "La réponse doit être un objet JSON avec exactement la clé 'questions' contenant une liste. "
                                "IMPORTANT: évite les répétitions. "
                                "Interdiction d'ajouter des suffixes comme '(Q12)'. "
                                "Varie les nombres, expressions et sous-thèmes autant que possible."
                            )
                            user_obj = {
                                "task": "generate_mcq",
                                "subject": subject,
                                "sector": sector,
                                "level": level,
                                "difficulty": difficulty,
                                "num_questions": missing,
                                "format": {
                                    "question": "string",
                                    "choices": ["string", "string", "string", "string"],
                                    "correct_answer": "A|B|C|D",
                                    "explanation": "string",
                                },
                                "constraints": {
                                    "choices_count": 4,
                                    "language": "fr",
                                    "no_markdown": True,
                                    "no_repeated_questions": True,
                                    "diversity": "high",
                                    "max_similarity": relax_sim,
                                    "nonce": nonce,
                                },
                            }

                            payload = {
                                "model": getattr(settings, "MISTRAL_MODEL", None) or "mistral-small-latest",
                                "temperature": 0.8,
                                "messages": [
                                    {"role": "system", "content": system},
                                    {"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)},
                                ],
                            }
                            headers = {
                                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                                "Content-Type": "application/json",
                            }

                            async with httpx.AsyncClient(timeout=60.0) as client:
                                r = await client.post(url, json=payload, headers=headers)
                                r.raise_for_status()
                                data = r.json()

                            content = None
                            try:
                                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                            except Exception:
                                content = None
                            if not content:
                                raise ValueError("Empty Mistral response")

                            raw_json = self._extract_json_object(content)
                            parsed = json.loads(raw_json)
                            qs = parsed.get("questions") if isinstance(parsed, dict) else None
                            if not isinstance(qs, list):
                                raise ValueError("Invalid Mistral questions format")

                            formatted_questions = []
                            for q in qs[: int(missing)]:
                                if not isinstance(q, dict):
                                    continue
                                q2 = {
                                    "question": q.get("question"),
                                    "choices": q.get("choices"),
                                    "correct_answer": q.get("correct_answer"),
                                    "explanation": q.get("explanation"),
                                }
                                q2 = self._coerce_correct_answer_to_letter(q2)
                                formatted_questions.append(q2)

                            # Relaxed: dedup by signature only, then allow slightly similar.
                            merged = self._dedup_only(collected + formatted_questions)
                            collected = merged
                            if len(collected) >= target_n:
                                return collected[:target_n]

                            # If we made progress, recompute missing and continue
                            if len(formatted_questions) > 0:
                                break
                        except Exception as e:
                            last_err = e
                            self._log.info("Mistral relax attempt failed: %s: %s", type(e).__name__, str(e))
                            try:
                                await asyncio.sleep(0.25)
                            except Exception:
                                pass

            # If we can't fill the requested size with diverse questions, fallback to local.
            if len(collected) < target_n:
                self._log.info(
                    "Mistral could not generate enough diverse questions (%d/%d), fallback to local bank. last_err=%s",
                    len(collected),
                    target_n,
                    str(last_err) if last_err else None,
                )
            else:
                return collected[:target_n]

            # Top up with local bank if possible (best-effort) rather than failing.
            try:
                missing = max(0, target_n - len(collected))
                if missing > 0:
                    local_more = generate_questions_by_subject(
                        subject=subject,
                        level=level,
                        num_questions=missing,
                        class_level=None,
                        sector=sector,
                        difficulty=difficulty,
                    )
                    merged = self._dedup_and_filter(list(collected) + list(local_more or []), max_similarity=float(getattr(self, "_max_allowed_similarity", 0.45)))
                    if len(merged) >= target_n:
                        return merged[:target_n]
                    # As last resort, allow adding remaining even if similar, to avoid crashing the API.
                    out = list(collected)
                    for q in (local_more or []):
                        if len(out) >= target_n:
                            break
                        if isinstance(q, dict):
                            out.append(q)
                    if len(out) >= 1:
                        return out[:target_n]
            except Exception as e:
                self._log.info("Local top-up after Mistral shortfall failed: %s: %s", type(e).__name__, str(e))
        else:
            # No Mistral API key or not mistral provider
            if provider == "mistral":
                self._log.error("LLM_PROVIDER is set to 'mistral' but MISTRAL_API_KEY is missing or empty. Please set MISTRAL_API_KEY in your environment.")
                raise ValueError("LLM_PROVIDER is set to 'mistral' but MISTRAL_API_KEY is missing. Set the key or change provider.")

        if use_llm and provider == "ollama":
            try:
                system = "Tu es un générateur de QCM. Tu dois répondre STRICTEMENT en JSON valide, sans texte autour. La réponse doit être un objet JSON avec exactement la clé 'questions' contenant une liste."
                user = {
                    "task": "generate_mcq",
                    "subject": subject,
                    "sector": sector,
                    "level": level,
                    "difficulty": difficulty,
                    "num_questions": num_questions,
                    "format": {
                        "question": "string",
                        "choices": ["string", "string", "string", "string"],
                        "correct_answer": "A|B|C|D",
                        "explanation": "string"
                    },
                    "constraints": {
                        "choices_count": 4,
                        "language": "fr",
                        "no_markdown": True,
                        "no_repeated_questions": True,
                        "no_repeated_correct_answers_pattern": True
                    }
                }

                attempts = 3
                min_unique_ratio = 0.85 if int(num_questions or 0) >= 10 else 0.7
                max_allowed_similarity = float(getattr(self, "_max_allowed_similarity", 0.45))
                last_err: Optional[Exception] = None

                for attempt in range(attempts):
                    nonce = f"{int(time.time() * 1000)}-{random.randint(0, 1_000_000)}-{attempt}"
                    user2 = dict(user)
                    user2["nonce"] = nonce
                    user2["constraints"] = dict(user.get("constraints") or {})
                    user2["constraints"]["nonce"] = nonce
                    user2["constraints"]["do_not_repeat"] = True
                    user2["constraints"]["diversity"] = "high"
                    user2["constraints"]["max_similarity"] = max_allowed_similarity

                    payload = {
                        "model": self.model,
                        "prompt": f"{system}\n\nIMPORTANT: Ne répète aucune question. Génère {int(num_questions)} questions toutes différentes. Évite les thèmes trop proches.\n\n{json.dumps(user2, ensure_ascii=False)}",
                        "stream": False,
                        "temperature": 0.9,
                    }

                    try:
                        resp = await self._make_request("/api/generate", payload)
                        raw = resp.get("response") if isinstance(resp, dict) else None
                        if not raw:
                            raise ValueError("Empty Ollama response")

                        data = json.loads(self._extract_json_object(raw))
                        questions = data.get("questions") if isinstance(data, dict) else None
                        if not isinstance(questions, list) or not questions:
                            raise ValueError("Invalid questions payload")

                        formatted_questions = []
                        for q in questions[:num_questions]:
                            if not isinstance(q, dict):
                                continue
                            q2 = {
                                "question": q.get("question"),
                                "choices": q.get("choices"),
                                "correct_answer": q.get("correct_answer"),
                                "explanation": q.get("explanation"),
                            }
                            q2 = self._coerce_correct_answer_to_letter(q2)
                            formatted_questions.append(q2)

                        formatted_questions = self._dedup_and_filter(formatted_questions, max_similarity=max_allowed_similarity)

                        if len(formatted_questions) < int(num_questions or 1):
                            raise ValueError(f"LLM returned too few questions: {len(formatted_questions)}/{num_questions}")

                        uniq_ratio = self._questions_uniqueness_ratio(formatted_questions)
                        max_sim = self._max_similarity_in_batch(formatted_questions)
                        if uniq_ratio < min_unique_ratio or max_sim > max_allowed_similarity:
                            raise ValueError(f"LLM returned too many duplicates or similar questions (unique_ratio={uniq_ratio:.2f}, max_similarity={max_sim:.2f})")

                        return formatted_questions[:num_questions]
                    except Exception as e:
                        last_err = e
                        # small backoff then retry with a new nonce
                        try:
                            await asyncio.sleep(0.25)
                        except Exception:
                            pass

                raise last_err or ValueError("LLM generation failed")
            except Exception as e:
                self._log.info("LLM generation failed, fallback to local bank: %s: %s", type(e).__name__, str(e))

        # Fallback: local question bank
        # Strict local banks: keep dimensions separated (level/class_level/sector/difficulty)
        # so there is no mixing across classes/years/pro sectors.
        class_level = None
        try:
            # The level string may include class level ("lycée - premiere")
            if isinstance(level, str) and " - " in level:
                parts = [p.strip() for p in level.split(" - ") if p.strip()]
                if len(parts) >= 2:
                    class_level = parts[1]
                    level = parts[0]
        except Exception:
            pass

        questions = generate_questions_by_subject(
            subject=subject,
            level=level,
            num_questions=int(num_questions),
            class_level=class_level,
            sector=sector,
            difficulty=difficulty,
        )

        # STRICT: apply semantic dedup/filter on local, and fail if we cannot
        # produce exactly the requested size without repetition.
        local_all = list(questions or [])
        questions = self._dedup_and_filter(local_all, max_similarity=float(getattr(self, "_max_allowed_similarity", 0.45)))
        target_n = int(num_questions or 0)
        if target_n > 0 and len(questions) < target_n:
            raise ValueError(
                f"Banque locale insuffisante: {len(questions)}/{target_n} questions uniques disponibles (zéro répétition requis)."
            )

        formatted_questions = []
        for q in questions:
            q2 = {
                "question": q.get("question"),
                "choices": q.get("choices"),
                "correct_answer": q.get("correct_answer"),
                "explanation": q.get("explanation"),
            }
            q2 = self._coerce_correct_answer_to_letter(q2)
            formatted_questions.append(q2)

        self._log.debug("Generated %s questions (fallback=%s)", len(formatted_questions), True)
        return formatted_questions

# Instance globale pour l'import
llm_service = LLMService()
