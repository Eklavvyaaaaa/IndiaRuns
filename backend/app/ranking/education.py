import json
import os
import re
from typing import Any


class EducationLayer:
    DEFAULT_CONFIG_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../config/education_scoring.json")
    )

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        self.tier_scores = {
            key: float(value)
            for key, value in self.config.get("tier_scores", {}).items()
        }
        self.elite_institution_patterns = tuple(
            self.config.get("elite_institution_patterns", [])
        )
        self.degree_rules = self.config.get("degree_rules", [])
        self.signal_blends = self.config.get("signal_blends", {})

    def score(self, candidate_row: dict, jd_analysis: dict[str, Any] | None = None) -> float:
        parsed_edu = self._safe_parse(candidate_row.get("education", "[]"))
        education = [item for item in parsed_edu if isinstance(item, dict)]
        if not education:
            return float(self.config.get("default_missing_score", 35.0))

        best_tier = max(self._institution_score(item) for item in education)
        best_degree = max(self._degree_score(item) for item in education)

        active_signals = {
            signal.get("name")
            for signal in (jd_analysis or {}).get("signals", [])
            if signal.get("polarity") == "positive"
        }

        blend = self._select_blend(active_signals)
        score = (best_tier * blend["tier"]) + (best_degree * blend["degree"])

        return max(0.0, min(100.0, score))

    def _institution_score(self, education_item: dict) -> float:
        tier = str(education_item.get("tier", "unknown") or "unknown").lower()
        institution = str(education_item.get("institution", "") or "").lower()

        if tier in self.tier_scores and tier != "unknown":
            return self.tier_scores[tier]

        if any(re.search(pattern, institution) for pattern in self.elite_institution_patterns):
            return 100.0

        return float(self.config.get("unknown_tier_score", 45.0))

    def _degree_score(self, education_item: dict) -> float:
        degree = str(education_item.get("degree", "") or "").lower()

        for rule in self.degree_rules:
            if any(re.search(r'\b' + re.escape(term) + r'\b', degree) for term in rule.get("terms", [])):
                return float(rule["score"])

        if degree:
            return float(self.config.get("fallback_degree_score", 60.0))
        return float(self.config.get("missing_degree_score", 45.0))

    def _select_blend(self, active_signals: set[str]) -> dict[str, float]:
        for signal_name, blend in self.signal_blends.items():
            if signal_name != "default" and signal_name in active_signals:
                return self._validated_blend(blend)
        return self._validated_blend(self.signal_blends.get("default", {}))

    def _validated_blend(self, blend: dict[str, float]) -> dict[str, float]:
        tier_weight = float(blend.get("tier", 0.55))
        degree_weight = float(blend.get("degree", 0.45))
        total = tier_weight + degree_weight
        if total <= 0:
            return {"tier": 0.55, "degree": 0.45}
        return {"tier": tier_weight / total, "degree": degree_weight / total}

    def _safe_parse(self, data) -> list:
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return []

    def _load_config(self, config_path: str) -> dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
