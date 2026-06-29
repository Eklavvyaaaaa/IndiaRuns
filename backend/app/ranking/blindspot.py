class BlindSpotEngine:
    def compute(self, jd_text: str, candidate_row: dict, capability_score: float) -> dict:
        """
        Computes the blindspot metrics.
        ATS Score uses naive keyword matching against the JD.
        """
        ats_score = self._naive_ats_score(jd_text, candidate_row)
        delta = capability_score - ats_score
        
        # Consider a candidate a "hidden gem" if their capability is much higher than ATS
        # e.g., delta > 20 points and capability > 60
        is_hidden_gem = (delta > 20.0) and (capability_score > 60.0)
        
        return {
            "ats_score": round(ats_score, 1),
            "capability_score": round(capability_score, 1),
            "delta": round(delta, 1),
            "is_hidden_gem": is_hidden_gem
        }
        
    def _naive_ats_score(self, jd_text: str, candidate_row: dict) -> float:
        jd_words = set(jd_text.lower().split())
        
        import json
        skills = json.loads(candidate_row.get("skills", "[]"))
        summary = candidate_row.get("summary", "").lower()
        
        cand_corpus = summary + " "
        for s in skills:
            cand_corpus += s.get("name", "").lower() + " "
            
        cand_words = set(cand_corpus.split())
        
        if not jd_words:
            return 0.0
            
        overlap = jd_words.intersection(cand_words)
        # Naive matching: overlap / total jd words
        # Real ATS do exact phrase matching, so this is a proxy
        score = (len(overlap) / len(jd_words)) * 100.0
        
        # ATS usually tops out early, apply a multiplier
        return min(100.0, score * 3.0)
