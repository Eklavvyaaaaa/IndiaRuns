"""
scoring.py — Master scoring pipeline.

Combines semantic similarity, career fit, skill trust, career velocity,
and location fit into a final JD-adaptive score. Applies penalties,
behavioral multiplier, and blindspot delta.
"""

import networkx as nx
import numpy as np

from src.config import PENALTIES, BLINDSPOT_BOOST_FACTOR
from src.skill_graph import score_skill_transfer
from src.feature_extractor import SkillClaim

def compute_ats_baseline(candidate: dict, features: dict, jd_skills: list[str]) -> float:
    """
    Simulates a traditional keyword-matching ATS score.
    Used to compute the BlindSpot delta.
    """
    if not jd_skills:
        return 0.5
        
    cand_skill_names = [s.get("name", "").lower().strip() for s in candidate.get("skills", [])]
    cand_skill_set = set(cand_skill_names)
    
    # 1. Keyword match ratio
    matches = sum(1 for s in jd_skills if s in cand_skill_set)
    keyword_score = matches / len(jd_skills)
    
    # 2. Title exact match
    title = candidate.get("profile", {}).get("current_title", "").lower()
    title_score = 1.0 if any(t in title for t in ["ai", "ml", "machine learning", "data scientist"]) else 0.2
    
    return keyword_score * 0.7 + title_score * 0.3

def compute_penalties(candidate: dict, features: dict) -> float:
    """Compute sum of disqualifier penalties."""
    penalty = 0.0
    
    if features.get("is_all_services", False):
        penalty += PENALTIES["all_services"]
        
    avg_tenure = features.get("avg_tenure_months", 0)
    num_roles = features.get("num_roles", 0)
    if num_roles >= 4 and avg_tenure < 18:
        penalty += PENALTIES["job_hopper"]
        
    # Note: pure_research, wrong_domain, llm_wrapper_only would be added
    # via deeper LLM/heuristic checks on description texts. For now we use
    # semantic fit as a proxy for these.
        
    return penalty

def compute_final_score(
    candidate: dict,
    features: dict,
    semantic_score: float,
    skill_graph: nx.Graph,
    weights: dict[str, float],
    jd_skills: list[str],
    skill_claims: list[SkillClaim],
    behavioral_multiplier: float
) -> tuple[float, dict]:
    """
    Master scoring function.
    Returns: (final_score, component_scores_dict)
    """
    from src.decay import apply_decay_batch
    
    # 1. Semantic Fit (passed in directly)
    norm_semantic = max(0.0, min(1.0, (semantic_score + 1) / 2)) # map [-1,1] to [0,1]
    
    # 2. Career Fit
    cand_skill_names = [s.name for s in skill_claims]
    transfer_score = score_skill_transfer(cand_skill_names, jd_skills, skill_graph)
    career_fit = (features["title_relevance"] * 0.4 + 
                 transfer_score * 0.4 + 
                 features["experience_fit"] * 0.2)
                 
    # 3. Skill Trust
    decayed_scores = apply_decay_batch(skill_claims)
    avg_decayed_skill = sum(decayed_scores) / len(decayed_scores) if decayed_scores else 0.0
    # Boost if they have many JD relevant skills
    jd_skill_ratio = min(1.0, features["jd_relevant_skill_count"] / max(1, len(jd_skills)))
    skill_trust = avg_decayed_skill * 0.5 + jd_skill_ratio * 0.5
    
    # 4. Career Velocity
    velocity_score = 0.5
    if features["has_promotions"]:
        velocity_score += 0.2
    if features["has_product_company_exp"]:
        velocity_score += 0.1
    if features["company_diversity"] >= 2:
        velocity_score += 0.1
    if features["avg_tenure_months"] > 24:
        velocity_score += 0.1
    velocity_score = min(1.0, velocity_score)
    
    # 5. Location Fit
    location_fit = features["location_fit"]
    
    # Base Weighted Score
    base_score = (
        norm_semantic * weights["semantic_fit"] +
        career_fit * weights["career_fit"] +
        skill_trust * weights["skill_trust"] +
        velocity_score * weights["career_velocity"] +
        location_fit * weights["location_fit"]
    )
    
    # Apply Penalties
    penalized_score = max(0.0, base_score + compute_penalties(candidate, features))
    
    # Apply Behavioral Multiplier
    behavioral_score = min(1.0, penalized_score * behavioral_multiplier)
    
    # BlindSpot Delta
    ats_score = compute_ats_baseline(candidate, features, jd_skills)
    blindspot_delta = max(0.0, behavioral_score - ats_score)
    final_score = min(1.0, behavioral_score + blindspot_delta * BLINDSPOT_BOOST_FACTOR)
    
    components = {
        "semantic_fit": norm_semantic,
        "career_fit": career_fit,
        "skill_trust": skill_trust,
        "career_velocity": velocity_score,
        "location_fit": location_fit,
        "base_score": base_score,
        "penalties": compute_penalties(candidate, features),
        "behavioral_multiplier": behavioral_multiplier,
        "behavioral_score": behavioral_score,
        "ats_score": ats_score,
        "blindspot_delta": blindspot_delta,
        "final_score": final_score
    }
    
    return final_score, components
