import json
import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SignalDefinition:
    name: str
    label: str
    cues: tuple[str, ...]
    weight_deltas: dict[str, float]
    positive_negation_exceptions: tuple[str, ...]


class JDAdaptiveWeightEngine:
    """
    JD-aware weight adapter.

    This is intentionally deterministic and explainable. It detects employer
    priorities from the JD, converts them into signal strengths, applies capped
    weight nudges, and normalizes the resulting score weights.
    """

    DEFAULT_CONFIG_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../config/jd_adaptive_signals.json")
    )

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        self.base_weights = self.config["base_weights"]
        self.weight_floor = float(self.config["weight_floor"])
        self.weight_cap = float(self.config["weight_cap"])
        self.negation_re = self._build_negation_re(self.config.get("negation_terms", []))
        self.signals = self._load_signals(self.config.get("signals", []))

    def analyze(self, jd_text: str) -> dict[str, Any]:
        sentences = self._sentences(jd_text)
        detected = []
        weights = dict(self.base_weights)

        for signal in self.signals:
            result = self._detect_signal(signal, sentences)
            if result["confidence"] <= 0:
                continue

            detected.append(result)
            if result["polarity"] == "positive":
                strength = result["strength"]
                for dimension, delta in signal.weight_deltas.items():
                    weights[dimension] = weights.get(dimension, 0.0) + (delta * strength)

        weights = self._normalize(weights)
        confidence = self._overall_confidence(detected)

        return {
            "mode": "adaptive",
            "signals": detected,
            "adaptive_weights": {key: round(value, 4) for key, value in weights.items()},
            "confidence": round(confidence, 3),
            "reasoning": self._reasoning(detected, weights),
            "warnings": self._warnings(detected),
        }

    def base_analysis(self) -> dict[str, Any]:
        weights = self._normalize(dict(self.base_weights))
        return {
            "mode": "normal",
            "signals": [],
            "adaptive_weights": {key: round(value, 4) for key, value in weights.items()},
            "confidence": 1.0,
            "reasoning": ["Normal ranking mode uses the default scoring mix without JD-adaptive boosts."],
            "warnings": [],
        }

    def apply_priority_overrides(
        self,
        analysis: dict[str, Any],
        priority_overrides: dict[str, float] | None,
    ) -> dict[str, Any]:
        if not priority_overrides:
            return analysis

        weights = dict(analysis["adaptive_weights"])
        applied = {}

        for dimension, priority in priority_overrides.items():
            if dimension not in weights:
                continue
            bounded_priority = min(5.0, max(0.0, float(priority)))
            if bounded_priority <= 0:
                continue
            weights[dimension] = weights[dimension] + (bounded_priority * 0.035)
            applied[dimension] = bounded_priority

        weights = self._normalize(weights)
        analysis = dict(analysis)
        analysis["adaptive_weights"] = {key: round(value, 4) for key, value in weights.items()}
        analysis["manual_priorities"] = applied

        if applied:
            priority_text = ", ".join(f"{key}={value:g}" for key, value in applied.items())
            analysis["reasoning"] = list(analysis.get("reasoning", [])) + [
                f"Recruiter priority controls applied: {priority_text}."
            ]

        return analysis

    def _detect_signal(self, signal: SignalDefinition, sentences: list[str]) -> dict[str, Any]:
        evidence = []
        negated_evidence = []

        for sentence in sentences:
            lower = sentence.lower()
            if any(cue in lower for cue in signal.cues):
                if any(exception in lower for exception in signal.positive_negation_exceptions):
                    evidence.append(sentence)
                elif self.negation_re.search(sentence):
                    negated_evidence.append(sentence)
                else:
                    evidence.append(sentence)

        if not evidence and not negated_evidence:
            return {
                "name": signal.name,
                "label": signal.label,
                "confidence": 0.0,
                "strength": 0.0,
                "polarity": "neutral",
                "supporting_evidence": [],
                "explanation": "",
            }

        selected = evidence or negated_evidence
        hit_count = len(selected)
        strength = min(1.0, 0.45 + (hit_count * 0.18))
        confidence = min(0.96, 0.55 + (hit_count * 0.14))
        polarity = "positive" if evidence else "negative"

        return {
            "name": signal.name,
            "label": signal.label,
            "confidence": round(confidence, 3),
            "strength": round(strength, 3),
            "polarity": polarity,
            "supporting_evidence": selected[:3],
            "explanation": self._explain_signal(signal.label, polarity, selected[:2]),
        }

    def _normalize(self, weights: dict[str, float]) -> dict[str, float]:
        bounded = {
            key: min(self.weight_cap, max(self.weight_floor, value))
            for key, value in weights.items()
        }
        total = sum(bounded.values()) or 1.0
        return {key: value / total for key, value in bounded.items()}

    def _overall_confidence(self, signals: list[dict[str, Any]]) -> float:
        if not signals:
            return 0.55
        positives = [s["confidence"] for s in signals if s["polarity"] == "positive"]
        if not positives:
            return 0.6
        return sum(positives) / len(positives)

    def _reasoning(self, signals: list[dict[str, Any]], weights: dict[str, float]) -> list[str]:
        if not signals:
            return ["No strong JD priority signals were detected, so base scoring weights were used."]

        active = [s for s in signals if s["polarity"] == "positive"]
        reasons = [
            f"{s['label']} detected with confidence {s['confidence']:.2f}; adaptive weights were adjusted."
            for s in active[:5]
        ]

        strongest = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:3]
        weight_text = ", ".join(f"{name}={value:.2f}" for name, value in strongest)
        reasons.append(f"Highest scoring priorities after normalization: {weight_text}.")
        return reasons

    def _warnings(self, signals: list[dict[str, Any]]) -> list[str]:
        warnings = []
        for signal in signals:
            if signal["polarity"] == "negative":
                warnings.append(f"{signal['label']} appears negated in the JD; no positive weight boost was applied.")
        return warnings

    def _explain_signal(self, label: str, polarity: str, evidence: list[str]) -> str:
        if polarity == "negative":
            return f"The JD mentions {label.lower()}, but the nearby wording appears to negate it."
        return f"The JD emphasizes {label.lower()} through: {' '.join(evidence)}"

    def _sentences(self, text: str) -> list[str]:
        compact = re.sub(r"\s+", " ", text or "").strip()
        if not compact:
            return []
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+|[\n\r]+", compact) if s.strip()]

    def _load_config(self, config_path: str) -> dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_signals(self, configured_signals: list[dict[str, Any]]) -> list[SignalDefinition]:
        return [
            SignalDefinition(
                name=item["name"],
                label=item["label"],
                cues=tuple(cue.lower() for cue in item.get("cues", [])),
                weight_deltas={key: float(value) for key, value in item.get("weight_deltas", {}).items()},
                positive_negation_exceptions=tuple(
                    exception.lower() for exception in item.get("positive_negation_exceptions", [])
                ),
            )
            for item in configured_signals
        ]

    def _build_negation_re(self, terms: list[str]) -> re.Pattern:
        escaped = [re.escape(term) for term in terms if term]
        if not escaped:
            return re.compile(r"a^")
        return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)
