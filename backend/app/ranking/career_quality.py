import json
import re

class CareerQualityLayer:
    """
    Career quality scoring based purely on data signals.
    No hardcoded company names. No hardcoded title bands.
    No stagnation penalties. No IT services bias.
    """

    LEADERSHIP_SIGNALS = [
        "led", "managed", "built team", "hired", "mentored", "directed",
        "oversaw", "headed", "grew team", "scaled", "founded", "established"
    ]
    IMPACT_SIGNALS = [
        "improved", "increased", "reduced", "delivered", "launched", "shipped",
        "drove", "achieved", "generated", "saved", "grew", "deployed", "built"
    ]
    SCOPE_SIGNALS = [
        "cross-functional", "company-wide", "global", "enterprise", "platform",
        "end-to-end", "architecture", "strategy", "roadmap", "full-stack"
    ]

    def score(self, candidate_row: dict) -> float:
        try:
            career = json.loads(candidate_row.get("career_history", "[]"))
        except Exception:
            return 50.0

        if not career:
            return 50.0

        score = 50.0
        total_months = sum(c.get("duration_months", 0) for c in career)
        num_roles = len(career)

        # 1. Tenure health
        if num_roles > 0:
            avg_tenure = total_months / num_roles
            if 18 <= avg_tenure <= 48:
                score += 15.0
            elif avg_tenure > 48:
                score += 8.0
            elif avg_tenure < 12:
                score -= 10.0

        # 2. Scope signal density per role
        # Sort chronologically (oldest to newest) to ensure consistent progression checks
        def _get_start_date(c):
            sd = c.get("start_date")
            return sd[:10] if sd else "9999-99-99"
        sorted_career = sorted(career, key=_get_start_date)

        scope_scores = []
        for role in sorted_career:
            desc = role.get("description", "").lower()
            if not desc:
                continue
            leadership_hits = sum(1 for s in self.LEADERSHIP_SIGNALS if s in desc)
            impact_hits = sum(1 for s in self.IMPACT_SIGNALS if s in desc)
            scope_hits = sum(1 for s in self.SCOPE_SIGNALS if s in desc)
            signal_density = (leadership_hits * 3 + impact_hits * 2 + scope_hits * 2)
            scope_scores.append(min(10.0, signal_density))

        if scope_scores:
            avg_scope = sum(scope_scores) / len(scope_scores)
            score += min(25.0, avg_scope * 2.5)

        # 3. Quantified impact evidence
        all_descriptions = " ".join([
            c.get("description", "") for c in career
        ]).lower()

        numeric_impacts = len(re.findall(
            r'\b\d+[\%x]|\b\d+\s*(?:percent|times|million|billion|k\b)',
            all_descriptions
        ))
        score += min(15.0, numeric_impacts * 3.0)

        # 4. Progression signal
        if len(scope_scores) >= 2:
            mid = len(scope_scores) // 2
            early_avg = sum(scope_scores[:mid]) / mid
            late_avg = sum(scope_scores[mid:]) / (len(scope_scores) - mid)
            if early_avg > late_avg:
                score += 10.0
            elif early_avg < late_avg - 2:
                score -= 5.0

        # 5. Multi-company breadth
        unique_companies = len(set(
            c.get("company", "").lower().strip()
            for c in career if c.get("company", "")
        ))
        if unique_companies >= 3:
            score += 5.0

        return round(max(0.0, min(100.0, score)), 1)