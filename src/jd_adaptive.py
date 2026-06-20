"""
jd_adaptive.py — JD-Adaptive Weight Engine.

Analyzes the job description to extract latent signals (urgency, growth, research, etc.)
and recalibrates the base scoring weights accordingly.
"""

from src.config import (
    BASE_WEIGHTS,
    SIGNAL_MAP,
    SIGNAL_DELTAS,
    WEIGHT_FLOOR,
    SIGNAL_NOISE_THRESHOLD
)

def compute_signal_strength(jd_text: str, keywords: list[str]) -> float:
    """
    Compute 0.0-1.0 strength of a signal based on keyword frequency in JD.
    """
    text_lower = jd_text.lower()
    count = 0
    for kw in keywords:
        count += text_lower.count(kw.lower())
    
    # Simple normalization: 3+ mentions is strong (1.0)
    strength = min(1.0, count / 3.0)
    return strength if strength >= SIGNAL_NOISE_THRESHOLD else 0.0

def derive_weights(jd_text: str) -> dict[str, float]:
    """
    Recalibrate base weights based on JD signals.
    """
    weights = BASE_WEIGHTS.copy()
    
    # 1. Extract signals
    signals = {}
    for signal_name, keywords in SIGNAL_MAP.items():
        signals[signal_name] = compute_signal_strength(jd_text, keywords)
        
    # 2. Apply deltas
    for signal_name, strength in signals.items():
        if strength > 0:
            deltas = SIGNAL_DELTAS.get(signal_name, {})
            for dim, delta in deltas.items():
                weights[dim] += delta * strength
                
    # 3. Apply floor
    for dim in weights:
        weights[dim] = max(WEIGHT_FLOOR, weights[dim])
        
    # 4. L1 Normalize
    total = sum(weights.values())
    for dim in weights:
        weights[dim] /= total
        
    return weights

# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_jd_1 = "We need someone to hit the ground running. Production deployment from day 1 is mandatory. Must be in Pune."
    test_jd_2 = "Looking for a PhD to advance the field with state of the art research. Fully remote."
    
    print("Base Weights:", BASE_WEIGHTS)
    
    w1 = derive_weights(test_jd_1)
    print("\nUrgent + Geo-strict JD Weights:", {k: round(v, 3) for k, v in w1.items()})
    
    w2 = derive_weights(test_jd_2)
    print("\nResearch JD Weights:", {k: round(v, 3) for k, v in w2.items()})
