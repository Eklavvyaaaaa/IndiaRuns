import re

from typing import Tuple, List

class RoleAlignmentLayer:
    def __init__(self):
        # Define mutually exclusive job families with extensive synonyms
        self.families = {
            "engineering": {"engineer", "developer", "programmer", "architect", "scientist", "researcher", "sde", "swe", "mlops", "devops"},
            "product": {"product manager", "project manager", "program manager", "product owner", "scrum master", "agile coach", "delivery manager", "pm"},
            "sales_marketing": {"sales", "account executive", "marketing", "growth", "bd", "business development"},
            "hr_recruiting": {"recruiter", "talent acquisition", "hr", "human resources", "sourcer", "people ops"}
        }
        
        # Terms indicating side-projects or learning rather than production experience
        self.tourist_terms = {
            "side project", "side-project", "playing with", "experimenting with", 
            "taking online courses", "self-learner", "bootcamp", "just learning", 
            "exploring", "tinkering", "hobby"
        }

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
            # Use word boundaries to avoid matching 'pm' in 'development'
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
                penalty += 50.0
                cand_fam_str = "/".join(cand_families).title()
                warnings.append(f"Major job family mismatch: Candidate is in {cand_fam_str} while JD requires {jd_family.title()}.")
                
        # 2. "Tourist" Penalty for Senior Roles
        jd_intro = jd_text[:500].lower()
        is_senior_role = any(keyword in jd_intro for keyword in ["senior", "founding", "lead", "principal", "director", "head"])
        
        if is_senior_role:
            tourist_hits = [t for t in self.tourist_terms if t in summary_lower]
            if tourist_hits:
                penalty += 40.0
                warnings.append(f"Experience level mismatch: JD requires Senior/Production experience, but candidate profile mentions: '{', '.join(tourist_hits)}'.")
                
        return penalty, warnings
