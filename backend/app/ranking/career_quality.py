import json

class CareerQualityLayer:
    def __init__(self):
        self.it_services = ["TCS", "Infosys", "Wipro", "Cognizant", "Accenture", "Mindtree", "IT Services"]
        self.product_keywords = ["product", "saas", "startup", "ai", "machine learning"]

    def score(self, candidate_row: dict) -> float:
        """
        Calculates Career Quality Score out of 100.
        Rewards product/AI/startups. Penalizes pure IT services.
        """
        career = json.loads(candidate_row.get("career_history", "[]"))
        if not career:
            return 50.0
            
        score = 50.0
        pure_it_services = True
        
        for role in career:
            company = role.get("company", "").lower()
            industry = role.get("industry", "").lower()
            desc = role.get("description", "").lower()
            
            is_it_service = any(it.lower() in company for it in self.it_services) or "it services" in industry
            if not is_it_service:
                pure_it_services = False
                
            if any(p in company or p in industry or p in desc for p in self.product_keywords):
                score += 15.0
                pure_it_services = False
                
        if pure_it_services:
            score -= 30.0
            
        return max(0.0, min(100.0, score))
