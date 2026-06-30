import json
import re
from collections import Counter


class JDRequirementFitLayer:
    """
    Scores how much candidate evidence directly covers the current JD.

    Semantic search catches meaning; this layer catches requirement coverage:
    skills, tools, certifications, domains, and important multi-word phrases
    from the JD that are present in the candidate's structured profile.
    """

    STOP_TERMS = {
        "ability",
        "across",
        "and",
        "are",
        "build",
        "candidate",
        "company",
        "develop",
        "engineer",
        "engineering",
        "experience",
        "good",
        "have",
        "looking",
        "must",
        "preferred",
        "required",
        "requirements",
        "responsibilities",
        "role",
        "senior",
        "skill",
        "skills",
        "strong",
        "team",
        "the",
        "with",
        "work",
        "years",
    }

    def __init__(self, model=None):
        self.model = model

    def score(self, jd_text: str, candidate_row: dict) -> float:
        jd_terms_dict = self._extract_jd_terms(jd_text)
        if not jd_terms_dict:
            return 50.0

        candidate_text = self._candidate_text(candidate_row)
        candidate_skills = self._candidate_skills(candidate_row)

        total_weight = 0.0
        matched_weight = 0.0

        jd_terms = list(jd_terms_dict.keys())
        
        # If model is available, use semantic matching
        if self.model and jd_terms:
            try:
                import numpy as np
                # Embed JD terms and candidate skills
                jd_embs = self.model.encode(jd_terms, normalize_embeddings=True)
                
                # We can embed the candidate skills as a list
                cand_skill_list = list(candidate_skills)
                if cand_skill_list:
                    cand_embs = self.model.encode(cand_skill_list, normalize_embeddings=True)
                else:
                    cand_embs = np.array([])

                for i, term in enumerate(jd_terms):
                    freq = jd_terms_dict[term]
                    weight = self._term_weight(term, freq)
                    total_weight += weight
                    
                    term_matched_weight = 0.0
                    
                    # Exact string match first
                    if term in candidate_skills:
                        term_matched_weight = weight
                    elif term in candidate_text:
                        term_matched_weight = weight * 0.85
                    elif self._soft_token_match(term, candidate_text):
                        term_matched_weight = weight * 0.45
                    else:
                        # Fallback to semantic similarity if no string match
                        if cand_embs.size > 0:
                            sims = np.dot(cand_embs, jd_embs[i])
                            max_sim = np.max(sims)
                            if max_sim > 0.82:
                                term_matched_weight = weight * float(max_sim) * 0.9

                    matched_weight += term_matched_weight

                if total_weight <= 0:
                    return 50.0

                coverage = matched_weight / total_weight
                return max(0.0, min(100.0, coverage * 100.0))
            except Exception:
                pass # Fallback to naive if model fails

        # Fallback naive matching
        for term, frequency in jd_terms_dict.items():
            weight = self._term_weight(term, frequency)
            total_weight += weight

            if term in candidate_skills:
                matched_weight += weight
            elif term in candidate_text:
                matched_weight += weight * 0.85
            elif self._soft_token_match(term, candidate_text):
                matched_weight += weight * 0.45

        if total_weight <= 0:
            return 50.0

        coverage = matched_weight / total_weight
        return max(0.0, min(100.0, coverage * 100.0))

    def _extract_jd_terms(self, jd_text: str) -> Counter:
        normalized = self._normalize(jd_text)
        words = [w for w in normalized.split() if len(w) > 1 and w not in self.STOP_TERMS]
        terms = Counter()

        for n in (3, 2, 1):
            for i in range(0, max(0, len(words) - n + 1)):
                term = " ".join(words[i:i + n]).strip()
                if self._is_useful_term(term):
                    terms[term] += 1

        # Prefer specific phrases over their single-token parts.
        phrase_parts = set()
        for term in terms:
            if " " in term:
                phrase_parts.update(term.split())

        for part in phrase_parts:
            if part in terms and len(part) < 5:
                del terms[part]

        return Counter(dict(terms.most_common(40)))

    def _candidate_text(self, row: dict) -> str:
        chunks = [
            row.get("title", ""),
            row.get("summary", ""),
        ]

        for field in ("skills", "career_history", "education"):
            for item in self._safe_parse(row.get(field, "[]")):
                if isinstance(item, dict):
                    chunks.extend(str(value) for value in item.values() if value)

        return self._normalize(" ".join(chunks))

    def _candidate_skills(self, row: dict) -> set[str]:
        skills = set()
        for skill in self._safe_parse(row.get("skills", "[]")):
            if isinstance(skill, dict) and skill.get("name"):
                skills.add(self._normalize(skill["name"]))
        return skills

    def _term_weight(self, term: str, frequency: int) -> float:
        token_count = len(term.split())
        specificity = 1.0 + (0.4 * max(0, token_count - 1))
        repetition = min(2.0, 1.0 + (frequency * 0.2))
        tech_bonus = 1.25 if any(char in term for char in ("+", "#", ".", "/")) else 1.0
        return specificity * repetition * tech_bonus

    def _soft_token_match(self, term: str, candidate_text: str) -> bool:
        tokens = [token for token in term.split() if len(token) >= 4]
        if not tokens:
            return False
        matches = sum(1 for token in tokens if token in candidate_text)
        return matches / len(tokens) >= 0.75

    def _is_useful_term(self, term: str) -> bool:
        if not term or term in self.STOP_TERMS:
            return False
        if len(term) < 3:
            return False
        if all(token in self.STOP_TERMS for token in term.split()):
            return False
        return True

    def _normalize(self, text: str) -> str:
        lowered = str(text or "").lower()
        lowered = lowered.replace("c++", "cplusplus").replace("c#", "csharp")
        lowered = re.sub(r"[^a-z0-9+#./ -]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _safe_parse(self, data) -> list:
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return []
