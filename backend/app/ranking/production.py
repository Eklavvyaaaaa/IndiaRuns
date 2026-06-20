import json

class ProductionReadinessLayer:
    def __init__(self):
        self.keywords = {
            "production", "deployment", "monitoring", "latency", 
            "scale", "a/b test", "serving", "high availability", 
            "throughput", "optimization", "ci/cd", "kubernetes", "docker"
        }

    def score(self, candidate_row: dict) -> float:
        """
        Calculates Production Readiness Score out of 100 based on presence of production 
        terms in skills, summary, and career history.
        """
        text_corpus = ""
        
        skills = json.loads(candidate_row.get("skills", "[]"))
        career = json.loads(candidate_row.get("career_history", "[]"))
        summary = candidate_row.get("summary", "")
        
        for s in skills:
            text_corpus += s.get("name", "").lower() + " "
            
        for c in career:
            text_corpus += c.get("title", "").lower() + " "
            text_corpus += c.get("description", "").lower() + " "
            
        text_corpus += summary.lower()
        
        matches = sum(1 for kw in self.keywords if kw in text_corpus)
        
        # Max out at 4 distinct keywords for a perfect score of 100
        score = min(100.0, (matches / 4.0) * 100.0)
        return score
