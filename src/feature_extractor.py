"""
feature_extractor.py — Extract structured, scoreable features from raw candidate JSON.

Converts the nested candidate dict into flat features that the scoring
pipeline can consume directly. This module is pure logic — no ML models,
no I/O, no side effects.
"""

from dataclasses import dataclass
from datetime import date, datetime

from src.config import (
    EXPERIENCE_RANGE,
    JD_RELEVANT_SKILL_NAMES,
    PREFERRED_COUNTRY,
    PREFERRED_LOCATIONS,
    REFERENCE_DATE,
    SERVICE_COMPANIES,
    TIER1_INDIAN_CITIES,
    TITLE_KEYWORDS_IRRELEVANT,
    TITLE_KEYWORDS_MODERATE,
    TITLE_KEYWORDS_STRONG,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SkillClaim:
    """Represents a single skill claim from a candidate's profile."""
    name: str                       # skill name, lowercased
    raw_score: float                # 0.0–1.0 computed from endorsements + duration
    months_since_last_use: float    # 0 = currently using
    months_of_total_usage: float    # total duration claimed
    proficiency_claimed: str        # 'beginner' / 'intermediate' / 'advanced' / 'expert'
    endorsement_count: int          # from platform


# ═══════════════════════════════════════════════════════════════════════════════
# Profile text extraction (for embedding)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_profile_text(candidate: dict) -> str:
    """
    Concatenate all meaningful text from a candidate's profile into a single
    string for sentence-transformer embedding.
    
    Combines: headline + summary + all career_history descriptions + skill names.
    This gives the embedding model the fullest picture of who this person is.
    """
    parts = []
    
    profile = candidate.get("profile", {})
    
    # Headline
    headline = profile.get("headline", "")
    if headline:
        parts.append(headline)
    
    # Summary
    summary = profile.get("summary", "")
    if summary:
        parts.append(summary)
    
    # Career history descriptions — the richest text
    for role in candidate.get("career_history", []):
        desc = role.get("description", "")
        if desc:
            title = role.get("title", "")
            company = role.get("company", "")
            prefix = f"{title} at {company}: " if title and company else ""
            parts.append(prefix + desc)
    
    # Skill names (helps embedding capture technical vocabulary)
    skill_names = [s.get("name", "") for s in candidate.get("skills", []) if s.get("name")]
    if skill_names:
        parts.append("Skills: " + ", ".join(skill_names))
    
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# Title relevance
# ═══════════════════════════════════════════════════════════════════════════════

def extract_title_relevance(candidate: dict) -> float:
    """
    Score 0.0–1.0 based on how relevant the candidate's current title is
    to the Senior AI Engineer role.
    
    This is the primary defense against keyword stuffers — an HR Manager
    with 9 AI skills still gets a low title score.
    """
    title = candidate.get("profile", {}).get("current_title", "").lower().strip()
    
    if not title:
        return 0.1  # Unknown title — slight penalty
    
    # Check strong matches first
    for keyword in TITLE_KEYWORDS_STRONG:
        if keyword in title:
            return 1.0
    
    # Check moderate matches
    for keyword in TITLE_KEYWORDS_MODERATE:
        if keyword in title:
            return 0.5
    
    # Check explicit irrelevant titles
    for keyword in TITLE_KEYWORDS_IRRELEVANT:
        if keyword in title:
            return 0.05  # Near-zero — this is almost certainly a keyword stuffer
    
    # Unknown title — give modest benefit of the doubt
    return 0.25


# ═══════════════════════════════════════════════════════════════════════════════
# Experience fit
# ═══════════════════════════════════════════════════════════════════════════════

def extract_experience_fit(candidate: dict) -> float:
    """
    Score 0.0–1.0 based on years of experience vs. JD range (5–9 years ideal).
    
    Gaussian-like falloff outside the ideal range, with a hard floor for
    very junior or very senior candidates.
    """
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    
    ideal_min = EXPERIENCE_RANGE["ideal_min"]
    ideal_max = EXPERIENCE_RANGE["ideal_max"]
    acceptable_min = EXPERIENCE_RANGE["acceptable_min"]
    acceptable_max = EXPERIENCE_RANGE["acceptable_max"]
    
    if ideal_min <= yoe <= ideal_max:
        return 1.0  # Sweet spot
    elif acceptable_min <= yoe < ideal_min:
        # Slightly junior — linear ramp from acceptable_min to ideal_min
        return 0.5 + 0.5 * (yoe - acceptable_min) / (ideal_min - acceptable_min)
    elif ideal_max < yoe <= acceptable_max:
        # Slightly senior — linear decay from ideal_max to acceptable_max
        return 0.5 + 0.5 * (acceptable_max - yoe) / (acceptable_max - ideal_max)
    elif yoe < acceptable_min:
        # Too junior
        return max(0.1, yoe / acceptable_min * 0.5)
    else:
        # Too senior (>15 years) — still has value but outside range
        return max(0.2, 0.5 - (yoe - acceptable_max) * 0.02)


# ═══════════════════════════════════════════════════════════════════════════════
# Location fit
# ═══════════════════════════════════════════════════════════════════════════════

def extract_location_fit(candidate: dict) -> float:
    """
    Score 0.0–1.0 based on location proximity to JD requirements.
    
    JD prefers: Pune/Noida (1.0), other Tier-1 Indian cities (0.8),
    India generally (0.6), willing to relocate (0.5), international (0.2).
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    location = profile.get("location", "").lower().strip()
    country = profile.get("country", "").lower().strip()
    willing_to_relocate = signals.get("willing_to_relocate", False)
    work_mode = signals.get("preferred_work_mode", "")
    
    # Check preferred cities (Pune/Noida)
    for city in PREFERRED_LOCATIONS:
        if city in location:
            return 1.0
    
    # Check Tier-1 Indian cities
    for city in TIER1_INDIAN_CITIES:
        if city in location:
            return 0.85
    
    # In India but not Tier-1
    if PREFERRED_COUNTRY in country or "india" in location:
        if willing_to_relocate:
            return 0.70
        return 0.55
    
    # International but willing to relocate
    if willing_to_relocate:
        return 0.35
    
    # International, not willing to relocate
    return 0.15


# ═══════════════════════════════════════════════════════════════════════════════
# Skill claims extraction (for decay processing)
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_raw_skill_score(skill: dict) -> float:
    """
    Compute a raw 0.0–1.0 score for a single skill based on
    endorsements and duration. This feeds into the decay layer.
    """
    endorsements = skill.get("endorsements", 0)
    duration = skill.get("duration_months", 0)
    proficiency = skill.get("proficiency", "beginner")
    
    # Proficiency base
    prof_scores = {"beginner": 0.2, "intermediate": 0.5, "advanced": 0.75, "expert": 0.95}
    base = prof_scores.get(proficiency, 0.3)
    
    # Endorsement factor: log-scaled, diminishing returns
    import math
    endorsement_factor = min(1.0, math.log1p(endorsements) / math.log1p(50))
    
    # Duration factor: longer usage = more credible (cap at 60 months)
    duration_factor = min(1.0, duration / 60.0)
    
    # Combine: proficiency drives the score, endorsements and duration validate it
    raw = base * 0.5 + endorsement_factor * 0.25 + duration_factor * 0.25
    
    return min(1.0, raw)


def extract_skill_claims(candidate: dict) -> list[SkillClaim]:
    """
    Convert the candidate's skills array into a list of SkillClaim objects
    ready for the decay layer.
    
    months_since_last_use is estimated from career history:
    - If the skill appears in a current role → 0
    - Otherwise → months since end of most recent relevant role
    """
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    
    # Check if candidate has a current role (for estimating last-use time)
    has_current_role = any(r.get("is_current", False) for r in career)
    
    claims = []
    for skill in skills:
        name = skill.get("name", "").lower().strip()
        if not name:
            continue
        
        raw_score = _compute_raw_skill_score(skill)
        duration = skill.get("duration_months", 0)
        proficiency = skill.get("proficiency", "beginner")
        endorsements = skill.get("endorsements", 0)
        
        # Estimate months since last use:
        # If they have a current role and the skill duration suggests recent use, assume 0.
        # Otherwise, make a rough estimate.
        if has_current_role and duration > 0:
            months_since = 0.0  # Assume actively used if they have a current job
        elif duration > 0:
            # Not currently employed — estimate based on last role end date
            months_since = _estimate_months_since_last_role(career)
        else:
            months_since = 24.0  # No duration claimed — assume stale
        
        claims.append(SkillClaim(
            name=name,
            raw_score=raw_score,
            months_since_last_use=months_since,
            months_of_total_usage=float(duration),
            proficiency_claimed=proficiency,
            endorsement_count=endorsements,
        ))
    
    return claims


def _estimate_months_since_last_role(career: list[dict]) -> float:
    """Estimate months since the candidate's last role ended."""
    if not career:
        return 36.0  # No career history — assume very stale
    
    latest_end = None
    for role in career:
        if role.get("is_current", False):
            return 0.0  # Currently employed
        end_str = role.get("end_date")
        if end_str:
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
                if latest_end is None or end_date > latest_end:
                    latest_end = end_date
            except (ValueError, TypeError):
                continue
    
    if latest_end is None:
        return 12.0  # Can't determine — moderate assumption
    
    delta = REFERENCE_DATE - latest_end
    return max(0.0, delta.days / 30.44)  # Convert to months


# ═══════════════════════════════════════════════════════════════════════════════
# Career features (for velocity scoring)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_career_features(candidate: dict) -> dict:
    """
    Extract career trajectory features for velocity scoring.
    
    Returns dict with:
    - num_roles: total number of roles
    - avg_tenure_months: average duration per role
    - total_career_months: sum of all role durations
    - has_promotions: bool — did title complexity increase over time?
    - company_diversity: number of distinct companies
    - has_product_company_exp: bool — worked at non-services companies
    - years_of_experience: from profile
    - is_all_services: bool — entire career at IT services
    """
    career = candidate.get("career_history", [])
    profile = candidate.get("profile", {})
    
    if not career:
        return {
            "num_roles": 0,
            "avg_tenure_months": 0,
            "total_career_months": 0,
            "has_promotions": False,
            "company_diversity": 0,
            "has_product_company_exp": False,
            "years_of_experience": profile.get("years_of_experience", 0),
            "is_all_services": False,
        }
    
    durations = [r.get("duration_months", 0) for r in career]
    companies = [r.get("company", "").lower().strip() for r in career]
    titles = [r.get("title", "").lower() for r in career]
    
    # Check for promotions: title "seniority" increase
    seniority_keywords = ["junior", "associate", "mid", "senior", "staff", "principal", "lead", "head", "director", "vp"]
    has_promotions = _detect_promotions(titles, seniority_keywords)
    
    # Check for service company careers
    service_count = sum(1 for c in companies if _is_service_company(c))
    is_all_services = service_count == len(companies) and len(companies) > 0
    has_product_company_exp = service_count < len(companies)
    
    return {
        "num_roles": len(career),
        "avg_tenure_months": sum(durations) / len(durations) if durations else 0,
        "total_career_months": sum(durations),
        "has_promotions": has_promotions,
        "company_diversity": len(set(companies)),
        "has_product_company_exp": has_product_company_exp,
        "years_of_experience": profile.get("years_of_experience", 0),
        "is_all_services": is_all_services,
    }


def _is_service_company(company_name: str) -> bool:
    """Check if a company name matches known IT services firms."""
    company_lower = company_name.lower().strip()
    for svc in SERVICE_COMPANIES:
        if svc in company_lower:
            return True
    return False


def _detect_promotions(titles: list[str], seniority_keywords: list[str]) -> bool:
    """
    Detect if title seniority increased over time (rough heuristic).
    Titles are in chronological order (earliest first based on career_history).
    """
    if len(titles) < 2:
        return False
    
    def seniority_level(title: str) -> int:
        for i, kw in enumerate(seniority_keywords):
            if kw in title:
                return i
        return 3  # Default to "mid" level
    
    levels = [seniority_level(t) for t in titles]
    # Check if any later role has higher seniority than an earlier one
    for i in range(len(levels) - 1):
        if levels[i + 1] > levels[i]:
            return True
    return False


def is_all_services(candidate: dict) -> bool:
    """Check if the candidate's entire career is at IT services firms."""
    career = candidate.get("career_history", [])
    if not career:
        return False
    
    companies = [r.get("company", "").lower().strip() for r in career]
    return all(_is_service_company(c) for c in companies)


# ═══════════════════════════════════════════════════════════════════════════════
# JD-relevant skill counting
# ═══════════════════════════════════════════════════════════════════════════════

def count_jd_relevant_skills(candidate: dict) -> int:
    """Count how many of the candidate's skills are JD-relevant."""
    skills = candidate.get("skills", [])
    count = 0
    for skill in skills:
        name = skill.get("name", "").lower().strip()
        if name in JD_RELEVANT_SKILL_NAMES:
            count += 1
        else:
            # Fuzzy check — any JD skill keyword in the skill name
            for jd_skill in JD_RELEVANT_SKILL_NAMES:
                if jd_skill in name or name in jd_skill:
                    count += 1
                    break
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# Combined feature extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_all_features(candidate: dict) -> dict:
    """
    Extract all structured features from a candidate into a single flat dict.
    
    This is the main entry point — call this once per candidate during
    pre-computation and cache the result.
    """
    career_feats = extract_career_features(candidate)
    
    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "title_relevance": extract_title_relevance(candidate),
        "experience_fit": extract_experience_fit(candidate),
        "location_fit": extract_location_fit(candidate),
        "jd_relevant_skill_count": count_jd_relevant_skills(candidate),
        "total_skills": len(candidate.get("skills", [])),
        **career_feats,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    import sys
    
    from src.data_loader import load_sample_candidates
    
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_candidates.json"
    candidates = load_sample_candidates(path, n=10)
    
    for c in candidates:
        features = extract_all_features(c)
        profile_text = extract_profile_text(c)
        skill_claims = extract_skill_claims(c)
        
        cid = features["candidate_id"]
        title = c["profile"]["current_title"]
        print(f"\n{'='*60}")
        print(f"{cid}: {title}")
        print(f"  Title relevance:    {features['title_relevance']:.2f}")
        print(f"  Experience fit:     {features['experience_fit']:.2f}")
        print(f"  Location fit:       {features['location_fit']:.2f}")
        print(f"  JD-relevant skills: {features['jd_relevant_skill_count']}/{features['total_skills']}")
        print(f"  All services:       {features['is_all_services']}")
        print(f"  Has product exp:    {features['has_product_company_exp']}")
        print(f"  Avg tenure:         {features['avg_tenure_months']:.0f} months")
        print(f"  Profile text len:   {len(profile_text)} chars")
        print(f"  Skill claims:       {len(skill_claims)}")
