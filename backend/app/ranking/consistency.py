import json

class ConsistencyLayer:
    def score(self, candidate_row: dict) -> float:
        """
        Calculates Consistency Score out of 100 based on alignment between
        title, career history, skills, and summary.
        """
        title = candidate_row.get("title", "").lower()
        summary = candidate_row.get("summary", "").lower()
        skills = json.loads(candidate_row.get("skills", "[]"))
        career = json.loads(candidate_row.get("career_history", "[]"))
        
        score = 100.0
        
        # If title mentions a role, is it in the summary or career?
        if title and len(title.split()) > 1:
            title_words = set(title.split())
            summary_words = set(summary.split())
            
            career_titles = set()
            for c in career:
                for w in c.get("title", "").lower().split():
                    career_titles.add(w)
                    
            overlap_summary = title_words.intersection(summary_words)
            overlap_career = title_words.intersection(career_titles)
            
            if not overlap_summary and not overlap_career:
                score -= 30.0
                
        # Are top skills mentioned in the summary or career?
        top_skills = [s.get("name", "").lower() for s in skills[:3]]
        career_corpus = " ".join([c.get("description", "").lower() for c in career])
        
        missing_skills = 0
        for ts in top_skills:
            if ts not in summary and ts not in career_corpus:
                missing_skills += 1
                
        score -= (missing_skills * 10.0)
        
        return max(0.0, score)
