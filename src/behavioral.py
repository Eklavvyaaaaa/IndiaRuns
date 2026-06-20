"""
behavioral.py — Behavioral signal multiplier.

Computes a multiplier (0.45–1.10) from the 23 Redrob signals.
Penalizes inactive "ghost" candidates, rewards highly engaged ones.
"""

from datetime import datetime
from src.config import BEHAVIORAL_CONFIG, REFERENCE_DATE

def _days_since(date_str: str) -> float:
    """Calculate days since a YYYY-MM-DD date."""
    if not date_str:
        return 999.0
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        return max(0.0, (REFERENCE_DATE - dt).days)
    except (ValueError, TypeError):
        return 999.0

def compute_behavioral_multiplier(signals: dict) -> float:
    """
    Compute a combined multiplier from behavioral signals.
    Starts at 1.0.
    """
    if not signals:
        multiplier = 0.8  # Mild penalty for missing signals completely
        return max(BEHAVIORAL_CONFIG["min_multiplier"], min(BEHAVIORAL_CONFIG["max_multiplier"], multiplier))
        
    multiplier = 1.0

    def parse_bool(v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return bool(v)
    
    def parse_float(v, default):
        try:
            if v is None:
                return default
            return float(v)
        except (ValueError, TypeError):
            return default

    # 1. Activity Score (inactivity penalty)
    last_active = signals.get("last_active_date", "")
    days_inactive = _days_since(last_active)
    open_to_work = parse_bool(signals.get("open_to_work_flag", False))

    if days_inactive > BEHAVIORAL_CONFIG["inactivity_hard_penalty_days"]:
        multiplier -= 0.30  # Very inactive (>6 mo)
    elif days_inactive > BEHAVIORAL_CONFIG["inactivity_soft_penalty_days"]:
        multiplier -= 0.15  # Inactive (>3 mo)
        
    if open_to_work:
        multiplier += 0.05

    # 2. Responsiveness
    response_rate = parse_float(signals.get("recruiter_response_rate"), 0.5)
    response_time = parse_float(signals.get("avg_response_time_hours"), 48.0)

    if response_rate < BEHAVIORAL_CONFIG["response_rate_low_threshold"]:
        multiplier -= 0.20  # Never responds
    elif response_rate < BEHAVIORAL_CONFIG["response_rate_mid_threshold"]:
        multiplier -= 0.05
        
    if response_time > BEHAVIORAL_CONFIG["response_time_slow_hours"]:
        multiplier -= 0.10

    # 3. Credibility
    if not parse_bool(signals.get("verified_email", False)):
        multiplier -= 0.05
    if not parse_bool(signals.get("linkedin_connected", False)):
        multiplier -= 0.05
        
    completeness = parse_float(signals.get("profile_completeness_score"), 0.5)
    if completeness > 0.9:
        multiplier += 0.02

    # 4. Availability
    notice_days = parse_float(signals.get("notice_period_days"), 30.0)
    if notice_days <= BEHAVIORAL_CONFIG["notice_period_ideal_days"]:
        multiplier += 0.03
    elif notice_days > BEHAVIORAL_CONFIG["notice_period_max_days"]:
        multiplier -= 0.15  # Hard to hire (>3 mo notice)

    # 5. Market signal
    gh_score = parse_float(signals.get("github_activity_score"), 0.0)
    if gh_score > BEHAVIORAL_CONFIG["github_score_strong"]:
        multiplier += 0.05
    elif gh_score > BEHAVIORAL_CONFIG["github_score_moderate"]:
        multiplier += 0.02

    return max(BEHAVIORAL_CONFIG["min_multiplier"], min(BEHAVIORAL_CONFIG["max_multiplier"], multiplier))

# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_signals = [
        # Perfect engaged candidate
        {
            "last_active_date": "2026-06-10",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.8,
            "avg_response_time_hours": 12,
            "verified_email": True,
            "linkedin_connected": True,
            "profile_completeness_score": 1.0,
            "notice_period_days": 15,
            "github_activity_score": 80
        },
        # Ghost candidate
        {
            "last_active_date": "2025-01-01",
            "open_to_work_flag": False,
            "recruiter_response_rate": 0.05,
            "avg_response_time_hours": 100,
            "verified_email": True,
            "linkedin_connected": False,
            "profile_completeness_score": 0.4,
            "notice_period_days": 90,
            "github_activity_score": 0
        }
    ]
    
    for i, sig in enumerate(test_signals):
        mult = compute_behavioral_multiplier(sig)
        print(f"Candidate {i+1} multiplier: {mult:.3f}")
