import json
import re

class CareerQualityLayer:
    def __init__(self):
        self.it_services = ["tcs", "infosys", "wipro", "cognizant", "accenture", "mindtree"]
        self.product_keywords = ["product", "saas", "startup", "ai", "machine learning"]

    def _get_seniority_band(self, title: str) -> int:
        title = title.lower()
        if any(w in title for w in ["intern", "junior", "jr", "associate", "trainee", "entry"]):
            return 1 # Junior
        if any(w in title for w in ["staff", "principal", "manager", "director", "head", "vp", "chief", "founder"]):
            return 4 # Staff / Leadership
        if any(w in title for w in ["senior", "sr", "lead"]):
            return 3 # Senior
        return 2 # Mid (Default)

    def score(self, candidate_row: dict) -> float:
        """
        Calculates Career Quality Score out of 100 based on Career Trajectory Velocity.
        Rewards rapid progression to Senior/Staff, penalizes long-term stagnation.
        """
        career = json.loads(candidate_row.get("career_history", "[]"))
        if not career:
            return 50.0
            
        score = 50.0
        
        # Sort career chronologically (oldest to newest)
        # Assuming the standard dataset format where career is ordered newest to oldest
        # We will just reverse it. If it's messy, we should theoretically sort by start_date
        career_chronological = list(reversed(career))
        
        total_exp_months = 0
        highest_band_reached = 1
        months_to_senior = None
        months_to_staff = None
        
        pure_it_services = True
        
        for role in career_chronological:
            duration = role.get("duration_months", 0)
            title = role.get("title", "")
            company = role.get("company", "").lower()
            industry = role.get("industry", "").lower()
            desc = role.get("description", "").lower()
            
            band = self._get_seniority_band(title)
            
            if band > highest_band_reached:
                highest_band_reached = band
                
            if band >= 3 and months_to_senior is None:
                months_to_senior = total_exp_months
                
            if band >= 4 and months_to_staff is None:
                months_to_staff = total_exp_months
                
            total_exp_months += duration
            
            # Legacy Company Type checks (reduced weight)
            is_it_service = any(it in company for it in self.it_services) or "it services" in industry
            if not is_it_service:
                pure_it_services = False
            if any(p in company or p in industry or p in desc for p in self.product_keywords):
                score += 5.0
                pure_it_services = False
                
        # 1. Career Velocity Boosts
        if highest_band_reached >= 4 and months_to_staff is not None:
            if months_to_staff <= 72: # Reached Staff/Manager in under 6 years
                score += 40.0
            elif months_to_staff <= 120: # Reached Staff in under 10 years
                score += 20.0
        elif highest_band_reached >= 3 and months_to_senior is not None:
            if months_to_senior <= 48: # Reached Senior in under 4 years
                score += 30.0
            elif months_to_senior <= 84: # Reached Senior in under 7 years
                score += 15.0
                
        # 2. Stagnation Penalties
        if total_exp_months >= 120 and highest_band_reached <= 2:
            # >10 years experience but still Junior/Mid
            score -= 40.0
        elif total_exp_months >= 84 and highest_band_reached <= 2:
            # >7 years experience but still Junior/Mid
            score -= 20.0
            
        # 3. Pure IT Services Penalty
        if pure_it_services:
            score -= 15.0
            
        return max(0.0, min(100.0, score))
