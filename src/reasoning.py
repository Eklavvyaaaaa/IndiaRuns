"""
reasoning.py — Generate fact-based, human-readable reasoning per candidate.

Uses structured data to avoid hallucination. References specific facts:
title, years, company, named skills, signal values, location.
"""

def generate_reasoning(
    candidate: dict, 
    rank: int, 
    final_score: float, 
    weights: dict[str, float], 
    components: dict[str, float],
    jd_skills: list[str]
) -> str:
    """
    Generate a concise, fact-based reasoning string.
    Avoids LLM hallucination by only using candidate data.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Candidate")
    yoe = profile.get("years_of_experience", 0)
    location = profile.get("location", "Unknown Location")
    
    # 1. Opening summary
    reasoning = [f"Rank {rank} (Score: {final_score*100:.1f}/100): {title} with {yoe} years of experience in {location}."]
    
    # 2. Key strengths
    strengths = []
    if components["semantic_fit"] > 0.8:
        strengths.append("Exceptional semantic alignment with JD requirements")
    if components["career_fit"] > 0.8:
        strengths.append("Strong career progression and title relevance")
    if components["skill_trust"] > 0.8:
        strengths.append("High trust in verified, non-decayed ML skills")
    if components["behavioral_multiplier"] > 1.05:
        strengths.append("Highly engaged and available (strong behavioral signals)")
        
    if strengths:
        reasoning.append("Strengths: " + ", ".join(strengths) + ".")
        
    # 3. BlindSpot highlight (if applicable)
    if components["blindspot_delta"] > 0.15:
        reasoning.append(f"BlindSpot identified: Candidate scores poorly on traditional keyword matching (ATS score: {components['ats_score']*100:.0f}) but shows strong latent capability.")
        
    # 4. Gaps / Weaknesses
    gaps = []
    if components["location_fit"] < 0.5:
        gaps.append(f"Location ({location}) requires relocation")
    if components["behavioral_multiplier"] < 0.8:
        gaps.append("Low recent engagement or responsiveness")
    if components["penalties"] < 0:
        gaps.append(f"Disqualifier penalty applied ({components['penalties']})")
            
    if gaps:
        reasoning.append("Considerations: " + ", ".join(gaps) + ".")
        
    return " ".join(reasoning)

# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_cand = {
        "profile": {"current_title": "Machine Learning Engineer", "years_of_experience": 6.5, "location": "Pune, India"}
    }
    test_comps = {
        "semantic_fit": 0.85, "career_fit": 0.90, "skill_trust": 0.88, 
        "behavioral_multiplier": 1.10, "blindspot_delta": 0.20, "ats_score": 0.40,
        "location_fit": 1.0, "penalties": 0.0
    }
    
    print(generate_reasoning(test_cand, 1, 0.92, {}, test_comps, []))
