import json
import re
import os
from typing import Tuple, List

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
                if any(t in target_title for t in terms):
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

    def penalize(self, jd_text: str, candidate_title: str, candidate_summary: str) -> Tuple[float, List[str]]:
        """
        Returns a penalty score and a list of warning reasons.
        Includes robust edge-case handling for job family mismatches and experience levels.
        """
        title_lower = candidate_title.lower()
        summary_lower = candidate_summary.lower()
        
        warnings = []
        penalty = 0.0
        
        jd_family = self._extract_jd_primary_family(jd_text)
        cand_families = self._get_candidate_families(title_lower)
        
        # 1. Job Family Mismatch Penalty
        if jd_family != "unknown" and cand_families:
            if jd_family not in cand_families:
                # E.g. JD is engineering, but candidate is pure product
                # To be less strict for "adjacent" tech roles, we check if both are in "technical_families"
                jd_is_tech = jd_family in self.taxonomy["technical_families"]
                cand_is_tech = any(f in self.taxonomy["technical_families"] for f in cand_families)
                
                if jd_is_tech and not cand_is_tech:
                    penalty += 70.0 # Non-technical candidate applying for technical role
                elif not jd_is_tech and cand_is_tech:
                    penalty += 50.0 # Technical applying for non-technical
                else:
                    penalty += 30.0 # Adjacent role mismatch (e.g., Backend applying for AI)
                    
                cand_fam_str = "/".join(cand_families).replace("_", " ").title()
                warnings.append(f"Job family mismatch: Candidate is {cand_fam_str} while JD requires {jd_family.replace('_', ' ').title()}.")
                
        # 2. "Tourist" Penalty for Senior Roles
        jd_intro = jd_text[:500].lower()
        is_senior_role = any(keyword in jd_intro for keyword in ["senior", "founding", "lead", "principal", "director", "head"])
        
        if is_senior_role:
            tourist_hits = [t for t in self.tourist_terms if t in summary_lower]
            if tourist_hits:
                penalty += 40.0
                warnings.append(f"Experience level mismatch: JD requires Senior/Production experience, but profile mentions: '{', '.join(tourist_hits)}'.")
                
        return penalty, warnings
