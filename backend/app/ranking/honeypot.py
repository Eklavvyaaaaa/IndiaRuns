import json
import re
import os
from collections import Counter
from src.decay import validate_temporal_claim
from src.config import REFERENCE_DATE

class HoneypotDetector:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), "../../config/taxonomy.json")
        with open(config_path, "r") as f:
            self.taxonomy = json.load(f)
            
        self.non_tech_families = []
        for family in self.taxonomy["non_technical_families"]:
            self.non_tech_families.extend(self.taxonomy["families"][family]["synonyms"])
            
        self.tech_words = set()
        for family in self.taxonomy["technical_families"]:
            self.tech_words.update(self.taxonomy["families"][family]["core_tech_words"])

    def detect(self, candidate_row: dict) -> tuple[bool, float, float]:
        """
        Runs comprehensive data integrity and honeypot detection rules.
        Returns (is_quarantined, penalty_score, profile_reliability)
        where profile_reliability is 0.0 to 1.0.
        """
        is_quarantined = False
        penalty = 0.0
        reliability_deductions = 0.0
        
        career = json.loads(candidate_row.get("career_history", "[]"))
        skills = json.loads(candidate_row.get("skills", "[]"))
        title = candidate_row.get("title", "").lower()
        summary = candidate_row.get("summary", "").lower()
        
        # 1. Total Experience Validation
        total_exp_months = sum(c.get("duration_months", 0) for c in career if c.get("duration_months"))
        max_possible_months = total_exp_months + 24 # Buffer for overlaps
        
        # Check if total experience claimed wildly exceeds the time since they started working
        import datetime
        earliest_date = None
        for c in career:
            sd = c.get("start_date")
            if sd:
                try:
                    d = datetime.datetime.strptime(sd[:10], "%Y-%m-%d").date()
                    if not earliest_date or d < earliest_date:
                        earliest_date = d
                except ValueError:
                    pass
        if earliest_date:
            true_career_months = max(1, (REFERENCE_DATE.year - earliest_date.year) * 12 + (REFERENCE_DATE.month - earliest_date.month))
            if total_exp_months > true_career_months * 1.8:
                penalty += 40.0
                reliability_deductions += 0.4
        
        # 2. Skill Support Verification & Temporal Anomalies
        career_corpus = " ".join([c.get("description", "").lower() for c in career])
        summary_corpus = summary
        
        extreme_duration_skills = 0
        expert_zero_duration = 0
        temporal_flags = 0
        
        for s in skills:
            s_name = s.get("name", "").lower()
            dur_months = s.get("duration_months", 0)
            prof = s.get("proficiency", "").lower()
            
            if dur_months > max_possible_months + 60:
                extreme_duration_skills += 1
                
            # Check for expert skills with zero duration
            if prof == "expert" and dur_months == 0:
                expert_zero_duration += 1
                
            # Temporal launch-date validation
            if s_name:
                validity = validate_temporal_claim(s_name, 0, dur_months)
                if validity == 0.0:
                    temporal_flags += 1
                elif validity == 0.5:
                    penalty += 10.0
                    
        if extreme_duration_skills > 5:
            penalty += 20.0
            reliability_deductions += 0.2
            
        if expert_zero_duration >= 2:
            penalty += 30.0
            reliability_deductions += 0.3
            
        if temporal_flags > 0:
            penalty += 50.0
            reliability_deductions += 0.5
            
        # 3. Concurrent Jobs Check
        current_jobs = sum(1 for c in career if c.get("is_current", False))
        if current_jobs >= 4:
            penalty += 40.0
            reliability_deductions += 0.3
            
        # 4. Career Title vs Description Contradictions (e.g., Graphic Designer with Kubeflow)
        for c in career:
            c_title = c.get("title", "").lower()
            c_desc = c.get("description", "").lower()
            
            is_non_tech = any(x in c_title for x in self.non_tech_families)
            if is_non_tech:
                tech_hits = sum(1 for w in self.tech_words if w in c_desc)
                if tech_hits > 1: # Require at least 2 distinct heavy-tech words
                    penalty += 50.0
                    reliability_deductions += 0.5
                    
        # 5. Reused / Templated descriptions across jobs
        descs = [c.get("description", "").strip() for c in career if len(c.get("description", "").strip()) > 30]
        if len(descs) > 1:
            desc_counts = Counter(descs)
            if desc_counts.most_common(1)[0][1] >= 3: # Must be copied 3+ times
                penalty += 10.0
                reliability_deductions += 0.1
                
        # Calculate Reliability
        profile_reliability = max(0.0, 1.0 - reliability_deductions)
        
        # 6. Anti-Gaming Detection (LLM phrasing & Keyword Stuffing)
        gaming_flags = []
        
        # LLM phrasing detection
        llm_phrases = [
            "delve into", "a testament to", "fostering", "innovative solutions",
            "seamless integration", "spearheaded", "synergy", "as an ai language model",
            "tapestry", "unwavering", "catalyst"
        ]
        llm_hits = sum(1 for phrase in llm_phrases if phrase in summary_corpus or phrase in career_corpus)
        if llm_hits >= 3:
            gaming_flags.append(f"Anti-Gaming: Flagged for generic LLM-style phrasing ({llm_hits} typical AI generation phrases found).")
            penalty += 15.0
            
        # Keyword density anomalies
        total_words = len(career_corpus.split()) + len(summary_corpus.split())
        if total_words > 50 and skills:
            top_skill = skills[0].get("name", "").lower()
            if top_skill and len(top_skill) > 2:
                skill_count = career_corpus.count(top_skill) + summary_corpus.count(top_skill)
                # If a single word appears more than once every 15 words, it's keyword stuffing
                if skill_count > 0 and (total_words / skill_count) < 15:
                    gaming_flags.append(f"Anti-Gaming: Keyword density anomaly detected for '{top_skill}' (appears {skill_count} times).")
                    penalty += 15.0
                    
        # Mismatched skill claims vs project evidence
        expert_unsupported = 0
        for s in skills:
            if s.get("proficiency", "").lower() == "expert":
                s_name = s.get("name", "").lower()
                if s_name and len(s_name) > 2 and s_name not in career_corpus:
                    expert_unsupported += 1
        
        if expert_unsupported >= 2:
             gaming_flags.append(f"Anti-Gaming: Mismatched claims ({expert_unsupported} 'expert' skills with no project evidence).")
             penalty += 20.0

        # Quarantine Check
        if profile_reliability < 0.3 or penalty >= 100.0:
            is_quarantined = True
            
        penalty = min(100.0, penalty)
        
        return is_quarantined, penalty, profile_reliability, gaming_flags
