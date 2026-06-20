import json

class BehavioralIntelligenceLayer:
    def score(self, candidate_row: dict) -> float:
        """
        Calculates Behavioral Intelligence Score out of 100 based on signals.
        """
        signals = json.loads(candidate_row.get("behavioral_signals", "{}"))
        
        score = 0.0
        
        # 1. Profile Completeness (max 20)
        comp = signals.get("profile_completeness_score", 0)
        score += min(20.0, (comp / 100.0) * 20.0)
        
        # 2. Open to Work (max 15)
        if signals.get("open_to_work_flag"):
            score += 15.0
            
        # 3. Recruiter Response Rate (max 20)
        rr = signals.get("recruiter_response_rate", 0)
        if rr > 0:
            score += min(20.0, rr * 20.0)
            
        # 4. GitHub Activity (max 15)
        gh = signals.get("github_activity_score", -1)
        if gh > 0:
            # Assume 10.0 is excellent
            score += min(15.0, (gh / 10.0) * 15.0)
            
        # 5. Interview Completion Rate (max 20)
        icr = signals.get("interview_completion_rate", 0)
        if icr > 0:
            score += min(20.0, icr * 20.0)
            
        # 6. Recency (Last active) (max 10)
        # We don't have datetime logic here easily without importing, so base it on 
        # whether they applied/viewed recently as proxies
        apps = signals.get("applications_submitted_30d", 0)
        views = signals.get("profile_views_received_30d", 0)
        if apps > 0 or views > 10:
            score += 10.0
            
        return min(100.0, score)
