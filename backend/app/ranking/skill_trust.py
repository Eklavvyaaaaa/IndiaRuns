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
            
        total_trust = 0.0
        for s in skills:
            endorsements = s.get("endorsements", 0)
            duration = s.get("duration_months", 0)
            
            # Base trust from duration (cap at 60 months = 1.0 multiplier)
            dur_score = min(duration / 60.0, 1.0) * 50.0
            
            # Trust from endorsements (cap at 20 = 1.0 multiplier)
            end_score = min(endorsements / 20.0, 1.0) * 50.0
            
            skill_score = dur_score + end_score
            total_trust += skill_score
            
        avg_skill_trust = total_trust / len(skills)
        
        # Boost if they have assessment scores
        assessments = signals.get("skill_assessment_scores", {})
        if assessments:
            avg_assessment = sum(assessments.values()) / len(assessments)
            # Boost up to 20 points
            avg_skill_trust += (avg_assessment / 100.0) * 20.0
            
        return min(100.0, avg_skill_trust)
