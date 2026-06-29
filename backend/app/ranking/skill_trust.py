import json

class SkillTrustLayer:
    def score(self, candidate_row: dict) -> float:
        """
        Calculates Skill Trust Score out of 100 based on endorsements,
        assessments, and duration.
        """
        skills = json.loads(candidate_row.get("skills", "[]"))
        signals = json.loads(candidate_row.get("behavioral_signals", "{}"))
        
        if not skills:
            return 0.0
            
        import math
        import datetime
        from src.config import REFERENCE_DATE, DECAY_RATES, DEFAULT_DECAY, SKILL_CATEGORIES

        def get_decay_rate(skill_name: str) -> float:
            skill_lower = skill_name.lower().strip()
            for keyword, category in SKILL_CATEGORIES.items():
                if keyword in skill_lower:
                    return DECAY_RATES.get(category, DEFAULT_DECAY)
            return DEFAULT_DECAY
            
        career = json.loads(candidate_row.get("career_history", "[]"))

        total_trust = 0.0
        for s in skills:
            s_name = s.get("name", "").lower()
            endorsements = s.get("endorsements", 0)
            duration = s.get("duration_months", 0)
            
            # Calculate months since last use
            most_recent_end_date = None
            is_currently_using = False
            for c in career:
                desc = c.get("description", "").lower()
                title = c.get("title", "").lower()
                if s_name in desc or s_name in title:
                    if c.get("is_current", False):
                        is_currently_using = True
                        break
                    ed = c.get("end_date")
                    if ed:
                        try:
                            d = datetime.datetime.strptime(ed[:10], "%Y-%m-%d").date()
                            if not most_recent_end_date or d > most_recent_end_date:
                                most_recent_end_date = d
                        except ValueError:
                            pass
            
            if is_currently_using:
                months_since_last_use = 0
            elif most_recent_end_date:
                months_since_last_use = max(0, (REFERENCE_DATE.year - most_recent_end_date.year) * 12 + (REFERENCE_DATE.month - most_recent_end_date.month))
            else:
                months_since_last_use = 12 # Default penalty if skill not explicitly found in career history
                
            lam = get_decay_rate(s_name)
            decay_factor = math.exp(-lam * months_since_last_use)
            
            # Base trust from duration (cap at 60 months = 1.0 multiplier)
            dur_score = min(duration / 60.0, 1.0) * 50.0
            
            # Trust from endorsements (cap at 20 = 1.0 multiplier)
            end_score = min(endorsements / 20.0, 1.0) * 50.0
            
            skill_score = (dur_score + end_score) * decay_factor
            total_trust += skill_score
            
        avg_skill_trust = total_trust / len(skills)
        
        # Boost if they have assessment scores
        assessments = signals.get("skill_assessment_scores", {})
        if assessments:
            avg_assessment = sum(assessments.values()) / len(assessments)
            # Boost up to 20 points
            avg_skill_trust += (avg_assessment / 100.0) * 20.0
            
        return min(100.0, avg_skill_trust)
