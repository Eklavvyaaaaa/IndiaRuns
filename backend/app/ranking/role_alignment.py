import json
import re
import os
from typing import Tuple, List

# AI/ML keywords used to detect if a JD is actually for an AI role
_AI_JD_KEYWORDS = {
    "machine learning", "deep learning", "artificial intelligence",
    "ai engineer", "ml engineer", "nlp", "computer vision",
    "neural network", "pytorch", "tensorflow", "langchain",
    "llm", "large language model", "embeddings", "vector database",
    "rag", "retrieval augmented", "fine-tuning", "transformer",
    "huggingface", "data scientist", "recommendation system",
}


def _is_ai_jd(jd_text: str) -> bool:
    """Returns True if the JD is clearly for an AI/ML role."""
    jd_lower = jd_text.lower()
    hits = sum(1 for kw in _AI_JD_KEYWORDS if kw in jd_lower)
    return hits >= 3  # Need at least 3 AI keywords to be considered an AI JD


class RoleAlignmentLayer:
    def __init__(self):
        # Load centralized taxonomy
        config_path = os.path.join(os.path.dirname(__file__), "../../config/taxonomy.json")
        with open(config_path, "r") as f:
            self.taxonomy = json.load(f)
            
        self.families = {k: set(v["synonyms"]) for k, v in self.taxonomy["families"].items()}
        self.tourist_terms = set(self.taxonomy["tourist_terms"])

    def _extract_jd_primary_family(self, jd_text: str) -> str:
        """
        Attempts to extract the primary job family from the very beginning of the JD.
        Looks for standard headers like 'Job Description: X', 'Role: X', 'Title: X'.
        """
        jd_intro = jd_text[:300].lower()
        
        # Look for the first explicit title declaration
        match = re.search(r'(job description|role|title|position):\s*([^\n]+)', jd_intro)
        if match:
            target_title = match.group(2)
            for family, terms in self.families.items():
                if any(re.search(rf'\b{re.escape(t)}\b', target_title) for t in terms):
                    return family
                    
        # Fallback: Count occurrences in the first 500 chars and take the max
        jd_head = jd_text[:500].lower()
        counts = {family: sum(1 for t in terms if t in jd_head) for family, terms in self.families.items()}
        max_family = max(counts, key=counts.get)
        if counts[max_family] > 0:
            return max_family
            
        return "unknown"

    def _get_candidate_families(self, title_lower: str) -> set:
        """Returns all job families that the candidate's title matches."""
        matched = set()
        for family, terms in self.families.items():
            if any(re.search(rf'\b{re.escape(t)}\b', title_lower) for t in terms):
                matched.add(family)
        return matched

    def _safe_parse(self, data) -> list:
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return []
        return []

    def penalize(self, jd_text: str, row: dict, pr_score: float) -> Tuple[float, List[str]]:
        """
        Returns a penalty score and a list of warning reasons.
        
        FLEXIBLE: AI-specific penalties (AI Tourist, Academic-only) are only applied
        when the JD is actually for an AI/ML role. Job family mismatch penalties
        are softened to avoid destroying good semantic matches from adjacent domains.
        """
        candidate_title = row.get("title", "")
        candidate_summary = row.get("summary", "")
        title_lower = candidate_title.lower()
        summary_lower = candidate_summary.lower()
        career = self._safe_parse(row.get("career_history", "[]"))
        skills = self._safe_parse(row.get("skills", "[]"))
        
        warnings = []
        penalty = 0.0
        
        is_ai_role = _is_ai_jd(jd_text)
        jd_family = self._extract_jd_primary_family(jd_text)
        cand_families = self._get_candidate_families(title_lower)
        
        # 0. Experience Band Disqualifier
        import re
        jd_lower_text = jd_text.lower()
        exp_min = 0.0
        range_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*(?:\+?\s*)?years?(?:\s+of)?\s+(?:experience|exp)', jd_lower_text)
        if range_match:
            exp_min = float(range_match.group(1))
        else:
            plus_match = re.search(r'(?:minimum|at least|min)?\s*(\d+)\s*\+?\s*years?(?:\s+of)?\s+(?:experience|exp)', jd_lower_text)
            if plus_match:
                exp_min = float(plus_match.group(1))

        if exp_min > 0:
            total_exp_months = sum(c.get("duration_months", 0) for c in career if c.get("duration_months"))
            total_exp_years = total_exp_months / 12.0
            
            if total_exp_years < exp_min - 0.5:
                shortfall = exp_min - total_exp_years
                penalty += min(60.0, 15.0 * shortfall)
                warnings.append(f"Experience Disqualifier: JD requires {exp_min}+ years, but candidate only has {total_exp_years:.1f} years.")

        # 1. Job Family Mismatch Penalty (SOFTENED)
        # Only apply strong penalties for clearly non-technical candidates
        # applying to technical roles. Adjacent tech roles get a gentle nudge.
        if jd_family != "unknown" and cand_families:
            if jd_family not in cand_families:
                jd_is_tech = jd_family in self.taxonomy.get("technical_families", [])
                cand_is_tech = any(f in self.taxonomy.get("technical_families", []) for f in cand_families)
                
                if jd_is_tech and not cand_is_tech:
                    # Non-technical candidate applying for technical role (big mismatch)
                    penalty += 50.0
                    cand_fam_str = "/".join(cand_families).replace("_", " ").title()
                    warnings.append(f"Job family mismatch: Candidate is {cand_fam_str} while JD requires {jd_family.replace('_', ' ').title()}.")
                elif not jd_is_tech and cand_is_tech:
                    # Technical applying for non-technical
                    penalty += 30.0
                    cand_fam_str = "/".join(cand_families).replace("_", " ").title()
                    warnings.append(f"Job family mismatch: Candidate is {cand_fam_str} while JD requires {jd_family.replace('_', ' ').title()}.")
                # Adjacent tech roles: NO penalty — let semantic score handle it
                    
        # 2. "Tourist" Penalty for Senior Roles (only for AI JDs)
        if is_ai_role:
            jd_intro = jd_text[:500].lower()
            is_senior_role = any(keyword in jd_intro for keyword in ["senior", "founding", "lead", "principal", "director", "head"])
            
            if is_senior_role:
                tourist_hits = [t for t in self.tourist_terms if t in summary_lower]
                if tourist_hits:
                    penalty += 40.0
                    warnings.append(f"Experience level mismatch: JD requires Senior/Production experience, but profile mentions: '{', '.join(tourist_hits)}'.")
                
        # 3. IT Services Disqualifier (universal — applies to all JDs)
        from src.config import SERVICE_COMPANIES
        if career:
            all_services = True
            for c in career:
                comp_lower = c.get("company", "").lower()
                if not any(sc in comp_lower for sc in SERVICE_COMPANIES):
                    all_services = False
                    break
            if all_services:
                penalty += 40.0
                warnings.append("IT Services Disqualifier: Candidate's entire career is at IT Services firms.")

        # 4. Academic/Research-Only Disqualifier (only for AI JDs)
        if is_ai_role:
            academic_titles = ["research scientist", "postdoc", "professor", "researcher", "phd"]
            is_academic = any(at in title_lower for at in academic_titles)
            if is_academic and pr_score < 45.0:
                penalty += 30.0
                warnings.append("Academic/Research Disqualifier: Academic role with low production readiness.")

        # 5. AI Tourist Check (ONLY for AI JDs)
        if is_ai_role:
            core_ml_months = 0
            core_ml_libs = ["pytorch", "tensorflow", "scikit-learn", "numpy", "pandas", "keras"]
            tourist_tech = ["langchain", "openai", "llamaindex", "gpt", "chatgpt"]
            has_tourist_tech = False
            
            for s in skills:
                s_name = s.get("name", "").lower()
                dur = s.get("duration_months", 0)
                if any(tt in s_name for tt in tourist_tech):
                    has_tourist_tech = True
                if any(cm in s_name for cm in core_ml_libs):
                    core_ml_months = max(core_ml_months, dur)
                    
            # Check for pre-LLM ML roles (before 2022-11)
            has_pre_llm_ml_role = False
            import datetime
            ml_titles = ["ml", "machine learning", "data scientist", "ai", "artificial intelligence", "nlp", "computer vision"]
            for c in career:
                sd = c.get("start_date")
                c_title = c.get("title", "").lower()
                if sd and any(mt in c_title for mt in ml_titles):
                    try:
                        d = datetime.datetime.strptime(sd[:10], "%Y-%m-%d").date()
                        if d < datetime.date(2022, 11, 1):
                            has_pre_llm_ml_role = True
                            break
                    except ValueError:
                        pass
                    
            if has_tourist_tech and core_ml_months < 12 and not has_pre_llm_ml_role:
                penalty += 30.0
                warnings.append("AI Tourist Disqualifier: Recent LLM skills but lacking foundational ML experience (<12m core libs) and no pre-LLM ML roles.")
                
        return penalty, warnings
