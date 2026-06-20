import json
from datetime import datetime

class HoneypotDetector:
    def detect(self, candidate_row: dict) -> tuple[bool, float]:
        """
        Runs honeypot detection rules.
        Returns (is_honeypot, penalty_score)
        """
        is_honeypot = False
        penalty = 0.0
        
        career = json.loads(candidate_row.get("career_history", "[]"))
        skills = json.loads(candidate_row.get("skills", "[]"))
        
        # Rule 1: Impossible skill durations (e.g. 100+ months when experience is 2 years)
        total_exp_months = 0
        for c in career:
            duration = c.get("duration_months", 0)
            if duration:
                total_exp_months += duration
                
        # Give some buffer for overlapping jobs
        max_possible_months = total_exp_months + 24
        
        for s in skills:
            if s.get("duration_months", 0) > max_possible_months:
                penalty += 40.0
                if s.get("duration_months", 0) > max_possible_months + 60:
                    is_honeypot = True
                    
        # Rule 2: Too many overlapping concurrent jobs
        current_jobs = sum(1 for c in career if c.get("is_current", False))
        if current_jobs >= 3:
            penalty += 50.0
            is_honeypot = True
            
        # Rule 3: Extreme keyword stuffing (100+ skills with high duration but low exp)
        if len(skills) > 50 and total_exp_months < 36:
            penalty += 30.0
            
        # Cap penalty
        penalty = min(100.0, penalty)
        
        return is_honeypot, penalty
