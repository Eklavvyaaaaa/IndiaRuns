import json
import datetime

REFERENCE_DATE = datetime.date(2025, 1, 1)

class BehavioralIntelligenceLayer:
    """
    Split into two clean signals:
    1. score() — work quality signals only, feeds into ranking
    2. responsiveness_score() — platform activity, for recruiter outreach only

    Open to work, response rate, profile views never affect ranking score.
    Only actual work evidence does.
    """

    def score(self, candidate_row: dict) -> float:
        try:
            signals = json.loads(candidate_row.get("behavioral_signals", "{}"))
        except Exception:
            return 50.0

        score = 50.0

        # 1. GitHub activity — external validation of actual work
        gh = signals.get("github_activity_score", -1)
        if gh > 0:
            score += min(20.0, (gh / 10.0) * 20.0)

        # 2. Skill assessment scores — platform verified competence
        assessments = signals.get("skill_assessment_scores", {})
        if assessments:
            avg_assessment = sum(assessments.values()) / len(assessments)
            score += min(15.0, (avg_assessment / 100.0) * 15.0)

        # 3. Profile completeness — proxy for professionalism
        completeness = signals.get("profile_completeness_score", 0)
        score += min(10.0, (completeness / 100.0) * 10.0)

        # 4. Recency of activity — are they actively in the market
        last_active = signals.get("last_active_date", "")
        if last_active:
            try:
                la_date = datetime.datetime.strptime(
                    last_active[:10], "%Y-%m-%d"
                ).date()
                days_inactive = (REFERENCE_DATE - la_date).days
                if days_inactive <= 7:
                    score += 5.0
                elif days_inactive <= 30:
                    score += 3.0
                elif days_inactive > 180:
                    score -= 5.0
            except ValueError:
                pass

        # 5. Interview completion rate — proxy for seriousness
        icr = signals.get("interview_completion_rate", 0)
        if icr > 0:
            score += min(10.0, icr * 10.0)

        return round(max(0.0, min(100.0, score)), 1)

    def responsiveness_score(self, candidate_row: dict) -> dict:
        """
        Purely for recruiter outreach prioritization.
        Never used in ranking score.
        """
        try:
            signals = json.loads(candidate_row.get("behavioral_signals", "{}"))
        except Exception:
            return {"responsiveness_score": 50.0, "recommendation": "standard outreach"}

        score = 0.0

        if signals.get("open_to_work_flag"):
            score += 40.0

        rr = signals.get("recruiter_response_rate", 0)
        score += min(40.0, rr * 40.0)

        apps = signals.get("applications_submitted_30d", 0)
        if apps > 0:
            score += 20.0

        score = min(100.0, score)

        if score >= 70:
            rec = "high priority outreach"
        elif score >= 40:
            rec = "standard outreach"
        else:
            rec = "low response likelihood"

        return {
            "responsiveness_score": round(score, 1),
            "recommendation": rec
        }