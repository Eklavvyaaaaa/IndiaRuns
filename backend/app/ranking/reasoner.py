import json

class ReasoningEngine:
    def generate(self, candidate_row: dict, scores: dict) -> list[str]:
        """
        Generates evidence-based reasoning bullets based ONLY on candidate data
        and structured signals. Never hallucinate.
        """
        reasons = []
        
        career = json.loads(candidate_row.get("career_history", "[]"))
        skills = json.loads(candidate_row.get("skills", "[]"))
        signals = json.loads(candidate_row.get("behavioral_signals", "{}"))
        
        # Experience
        total_exp_months = sum(c.get("duration_months", 0) for c in career)
        if total_exp_months > 0:
            years = round(total_exp_months / 12.0, 1)
            reasons.append(f"{years} years of total experience extracted from career history")
            
        # Retrieval Score High
        if scores.get("retrieval_intelligence", 0) > 60:
            reasons.append("Strong evidence of production retrieval systems and vector database experience")
            
        # Production Readiness
        if scores.get("production_readiness", 0) > 60:
            reasons.append("Demonstrated background in scaling, deployment, and high-availability systems")
            
        # Behavioral
        rr = signals.get("recruiter_response_rate", 0)
        if rr > 0.8:
            reasons.append("High recruiter responsiveness (over 80% response rate)")
            
        # Skills
        top_skills = [s.get("name") for s in skills[:2]]
        if top_skills:
            reasons.append(f"Primary expertise in {', '.join(top_skills)}")
            
        # Honeypot
        if scores.get("honeypot_penalty", 0) > 0:
            reasons.append(f"WARNING: Profile flagged by honeypot detector (Penalty: {scores.get('honeypot_penalty')})")
            
        return reasons
