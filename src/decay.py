"""
decay.py — Skill half-life decay function.

Skills are not permanent assets. This module applies time-based exponential
decay to skill claims. For example, LLM tooling skills decay faster than
foundational math skills. Also includes the temporal honeypot filter.
"""

import math

from src.config import DEFAULT_DECAY, DECAY_RATES, SKILL_CATEGORIES, SKILL_LAUNCH_DATES, REFERENCE_DATE
from src.feature_extractor import SkillClaim

def get_decay_rate(skill_name: str) -> float:
    """Lookup λ for a skill, with fuzzy category matching."""
    skill_lower = skill_name.lower().strip()
    for keyword, category in SKILL_CATEGORIES.items():
        if keyword in skill_lower:
            return DECAY_RATES.get(category, DEFAULT_DECAY)
    return DEFAULT_DECAY

def apply_decay(claim: SkillClaim) -> float:
    """
    Compute effective skill score with half-life decay.
    Also applies usage-duration floor and honeypot penalties.
    """
    lam = get_decay_rate(claim.name)
    t = claim.months_since_last_use

    # Core exponential decay
    decay_factor = math.exp(-lam * t)

    # Usage duration credibility floor:
    # Expert claim with <6 months usage → cap score at 0.40
    # Intermediate with <3 months → cap at 0.30
    duration_cap = 1.0
    if claim.proficiency_claimed == 'expert' and claim.months_of_total_usage < 6:
        duration_cap = 0.40   # kills honeypot stuffing
    elif claim.proficiency_claimed == 'advanced' and claim.months_of_total_usage < 4:
        duration_cap = 0.50
    elif claim.proficiency_claimed == 'intermediate' and claim.months_of_total_usage < 3:
        duration_cap = 0.30

    # Endorsement boost: every 10 endorsements adds 3% (max +15%)
    endorsement_factor = 1.0 + min(0.15, claim.endorsement_count * 0.003)

    effective = claim.raw_score * decay_factor * endorsement_factor
    return min(effective, claim.raw_score * duration_cap)

def parse_ym(ym_str: str):
    """Parse 'YYYY-MM' to a (year, month) tuple for easy comparison."""
    parts = ym_str.split('-')
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 1970, 1

def months_between(ym1, ym2):
    """Calculate months between (Y, M) and (Y, M)"""
    return (ym1[0] - ym2[0]) * 12 + (ym1[1] - ym2[1])

def validate_temporal_claim(skill_name: str, claimed_months_ago: float, duration_months: float) -> float:
    """
    Returns a validity multiplier: 1.0 = plausible, 0.0 = impossible.
    Flags candidates for the honeypot detection log.
    
    Instead of claimed_start_date, we infer the start date from:
    REFERENCE_DATE - (claimed_months_ago + duration_months) months
    """
    skill_lower = skill_name.lower().strip()
    
    # Calculate the inferred start date in months relative to year 0
    ref_months = REFERENCE_DATE.year * 12 + REFERENCE_DATE.month
    inferred_start_months = ref_months - claimed_months_ago - duration_months
    inferred_start_ym = (int(inferred_start_months // 12), int(inferred_start_months % 12) or 1)
    
    for skill_key, launch_str in SKILL_LAUNCH_DATES.items():
        if skill_key in skill_lower:
            launch_ym = parse_ym(launch_str)
            if inferred_start_ym < launch_ym:
                delta_months = months_between(launch_ym, inferred_start_ym)
                if delta_months > 6:   # >6mo before ecosystem existed
                    return 0.0         # hard honeypot flag
                return 0.50            # borderline — soft penalty
    return 1.0   # no issue

def apply_decay_batch(claims: list[SkillClaim]) -> list[float]:
    """Process decay for a batch of skill claims."""
    return [apply_decay(c) for c in claims]

# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from src.feature_extractor import SkillClaim
    
    test_claims = [
        SkillClaim(name="pytorch", raw_score=0.90, months_since_last_use=4, months_of_total_usage=36, proficiency_claimed="expert", endorsement_count=50),
        SkillClaim(name="pytorch", raw_score=0.90, months_since_last_use=36, months_of_total_usage=36, proficiency_claimed="expert", endorsement_count=50),
        SkillClaim(name="langchain", raw_score=0.85, months_since_last_use=2, months_of_total_usage=12, proficiency_claimed="advanced", endorsement_count=20),
        SkillClaim(name="langchain", raw_score=0.85, months_since_last_use=12, months_of_total_usage=12, proficiency_claimed="advanced", endorsement_count=20),
        SkillClaim(name="statistics", raw_score=0.80, months_since_last_use=48, months_of_total_usage=60, proficiency_claimed="expert", endorsement_count=10),
    ]
    
    print("Decay Test Results:")
    for c in test_claims:
        eff = apply_decay(c)
        print(f"  {c.name:15s} (t={c.months_since_last_use:2d}m): {eff:.3f} (raw: {c.raw_score})")

    # Honeypot test
    # Claiming langchain 48 months ago with 12 months duration (started 60 months ago ~ 2021)
    validity = validate_temporal_claim("langchain", 48, 12)
    print(f"\nLangchain 5 years ago validity: {validity}")
