class BlindSpotEngine:
    def compute(self, jd_text: str, candidate_row: dict, capability_score: float) -> dict:
        """
        Computes the blindspot metrics.
        ATS Score uses naive keyword matching against the JD.
        """
        jd_words, cand_words, overlap = self._get_word_sets(jd_text, candidate_row)
        
        # Calculate naive ATS score
        if not jd_words:
            ats_score = 0.0
        else:
            score = (len(overlap) / len(jd_words)) * 100.0
            ats_score = min(100.0, score * 3.0)
            
        delta = capability_score - ats_score
        
        # Consider a candidate a "hidden gem" if their capability is much higher than ATS
        # e.g., delta > 20 points and capability > 60
        is_hidden_gem = (delta > 20.0) and (capability_score > 60.0)
        
        # Extract blindspots (missing keywords/skills)
        missing_terms = list(jd_words.difference(cand_words))
        
        # Filter out common stop words to get actual skill gaps
        stop_words = {"the", "and", "a", "to", "of", "in", "for", "is", "on", "that", "by", "this", "with", "i", "you", "it", "not", "or", "be", "are", "from", "at", "as", "your", "all", "have", "new", "more", "an", "was", "we", "will", "home", "can", "us", "about", "if", "page", "my", "has", "search", "free", "but", "our", "one", "other", "do", "no", "information", "time", "they", "site", "he", "up", "may", "what", "which", "their", "news", "out", "use", "any", "there", "see", "only", "so", "his", "when", "contact", "here", "business", "who", "web", "also", "now", "help", "get", "pm", "view", "online", "c", "e", "first", "am", "been", "would", "how", "were", "me", "s", "services", "some", "these", "click", "its", "like", "service", "x", "than", "find", "price", "date", "back", "top", "people", "had", "list", "name", "just", "over", "state", "year", "day", "into", "email", "two", "health", "n", "world", "re", "next", "used", "go", "b", "work", "last", "most", "products", "music", "buy", "data", "make", "them", "should", "product", "system", "post", "her", "city", "t", "add", "policy", "number", "such", "please", "available", "copyright", "support", "message", "after", "best", "software", "then", "jan", "good", "video", "well", "d", "where", "info", "rights", "public", "books", "high", "school", "through", "m", "each", "links", "she", "review", "years", "order", "very", "privacy", "book", "items", "company", "read", "group", "sex", "need", "many", "user", "said", "de", "does", "set", "under", "general", "research", "university", "january", "mail", "full", "map", "reviews", "program", "life", "experience", "required", "role", "looking", "candidate", "ability", "strong"}
        
        actual_blindspots = [term for term in missing_terms if len(term) > 3 and term not in stop_words]
        actual_blindspots.sort()
        
        return {
            "ats_score": round(ats_score, 1),
            "capability_score": round(capability_score, 1),
            "delta": round(delta, 1),
            "is_hidden_gem": is_hidden_gem,
            "blindspots": actual_blindspots[:5] # Top 5 missing skills
        }
        
    def _get_word_sets(self, jd_text: str, candidate_row: dict) -> tuple[set, set, set]:
        jd_words = set(jd_text.lower().split())
        
        import json
        skills = json.loads(candidate_row.get("skills", "[]"))
        summary = candidate_row.get("summary", "").lower()
        
        cand_corpus = summary + " "
        for s in skills:
            cand_corpus += s.get("name", "").lower() + " "
            
        cand_words = set(cand_corpus.split())
        
        if not jd_words:
            return jd_words, cand_words, set()
            
        overlap = jd_words.intersection(cand_words)
        return jd_words, cand_words, overlap
