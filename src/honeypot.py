"""
honeypot.py — Honeypot detection layer.

Detects impossible candidates by checking logical consistency:
1. Duration vs proficiency (expert with 0 duration)
2. Career timeline (claimed total duration > career length)
3. Skill density (too many expert skills for years of experience)
"""

from src.config import HONEYPOT_CONFIG

def check_skill_duration_consistency(candidate: dict) -> float:
    """Flag if candidate claims multiple expert skills with 0 duration."""
    skills = candidate.get("skills", [])
    zero_duration_experts = 0
    for s in skills:
        if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0:
            zero_duration_experts += 1
            
    if zero_duration_experts >= HONEYPOT_CONFIG["expert_zero_duration_threshold"]:
        return 1.0  # Hard fail
    elif zero_duration_experts > 0:
        return 0.4  # Suspicious
    return 0.0

def check_career_timeline(candidate: dict) -> float:
    """Flag if sum of career role durations vastly exceeds claimed YoE."""
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    
    yoe = profile.get("years_of_experience", 0)
    total_career_months = sum(r.get("duration_months", 0) for r in career)
    
    if yoe == 0:
        return 0.0 # Unknown, don't penalize
        
    claimed_career_months = yoe * 12
    ratio = total_career_months / claimed_career_months if claimed_career_months > 0 else 0
    
    if ratio > HONEYPOT_CONFIG["career_duration_mismatch_ratio"]:
        return 1.0  # Example: claims 3 years exp, but roles add up to 8 years
    elif ratio > 1.3:
        return 0.3
    return 0.0

def check_skill_density(candidate: dict) -> float:
    """Flag if candidate claims too many expert skills for their YoE."""
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    
    yoe = profile.get("years_of_experience", 0)
    if yoe == 0:
        return 0.0
        
    expert_count = sum(1 for s in skills if s.get("proficiency") == "expert")
    ratio = expert_count / yoe
    
    if ratio > HONEYPOT_CONFIG["max_expert_skills_per_year"]:
        return 0.8
    elif ratio > HONEYPOT_CONFIG["max_expert_skills_per_year"] * 0.7:
        return 0.4
    return 0.0

def compute_honeypot_score(candidate: dict) -> float:
    """Compute an overall honeypot score (0.0 to 1.0)."""
    score1 = check_skill_duration_consistency(candidate)
    score2 = check_career_timeline(candidate)
    score3 = check_skill_density(candidate)
    
    # Check temporal validity using decay.py (if available)
    temporal_score = 0.0
    try:
        from src.decay import validate_temporal_claim
        from src.feature_extractor import _estimate_months_since_last_role
        months_since = _estimate_months_since_last_role(candidate.get("career_history", []))
        for s in candidate.get("skills", []):
            dur = s.get("duration_months", 0)
            validity = validate_temporal_claim(s.get("name", ""), months_since, dur)
            if validity == 0.0:
                temporal_score = 1.0
                break
    except ImportError:
        pass
        
    # Take max (any single hard fail triggers the honeypot)
    return max(score1, score2, score3, temporal_score)

def is_likely_honeypot(candidate: dict, threshold: float = None) -> bool:
    """Return True if the candidate is considered a honeypot."""
    if threshold is None:
        threshold = HONEYPOT_CONFIG["honeypot_score_threshold"]
    return compute_honeypot_score(candidate) >= threshold
    
# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_cand = {
        "candidate_id": "HONEYPOT_001",
        "profile": {"years_of_experience": 2},
        "career_history": [
            {"duration_months": 48, "title": "Senior Engineer"},
            {"duration_months": 36, "title": "Engineer"}
        ], # 84 months (7 years) but claimed 2 YoE
        "skills": [
            {"name": "Python", "proficiency": "expert", "duration_months": 0},
            {"name": "ML", "proficiency": "expert", "duration_months": 0},
            {"name": "Langchain", "proficiency": "expert", "duration_months": 60} # temporal fail
        ]
    }
    
    score = compute_honeypot_score(test_cand)
    is_hp = is_likely_honeypot(test_cand)
    print(f"Honeypot score: {score:.2f}")
    print(f"Is honeypot: {is_hp}")
