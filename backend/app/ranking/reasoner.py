import json
import datetime
from src.config import (
    SERVICE_COMPANIES, REFERENCE_DATE,
    BEHAVIORAL_CONFIG
)


def _extract_jd_skills(jd_text: str) -> set[str]:
    """
    Dynamically extract skill-like keywords from the JD text.
    Instead of relying on a hardcoded list, we tokenize the JD and
    match against the candidate's actual skill names at scoring time.
    """
    return set(jd_text.lower().split())


def _extract_experience_range(jd_text: str) -> tuple[float, float]:
    """
    Dynamically parse experience requirements from the JD text.
    Looks for patterns like '3+ years', 'minimum 5 years', '5-10 years'.
    Returns (min_years, max_years). Defaults to (0, 99) if not found.
    """
    import re
    jd_lower = jd_text.lower()

    # Pattern: "X-Y years" or "X to Y years"
    range_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*(?:\+?\s*)?years?', jd_lower)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))

    # Pattern: "X+ years" or "minimum X years" or "at least X years"
    plus_match = re.search(r'(?:minimum|at least|min)?\s*(\d+)\s*\+?\s*years?', jd_lower)
    if plus_match:
        min_yrs = float(plus_match.group(1))
        return min_yrs, min_yrs + 10.0  # generous upper bound

    return 0.0, 99.0  # No constraint found


class ReasoningEngine:
    def generate(self, candidate_row: dict, scores: dict, jd_text: str = "", blindspot: dict = None) -> list[str]:
        """
        Generates evidence-based, organic reasoning bullets grounded
        entirely in the candidate's actual data. Never hallucinate.
        
        jd_text is used to dynamically determine which skills are relevant
        instead of relying on a hardcoded skill list.
        """
        reasons = []

        career = json.loads(candidate_row.get("career_history", "[]"))
        skills = json.loads(candidate_row.get("skills", "[]"))
        signals = json.loads(candidate_row.get("behavioral_signals", "{}"))
        title = candidate_row.get("title", "")
        summary = candidate_row.get("summary", "")

        jd_words = _extract_jd_skills(jd_text) if jd_text else set()
        exp_min, exp_max = _extract_experience_range(jd_text) if jd_text else (0, 99)

        # ── 1. Career trajectory summary ──────────────────────────────
        total_months = sum(c.get("duration_months", 0) for c in career)
        years = round(total_months / 12.0, 1) if total_months else 0

        if career:
            current = [c for c in career if c.get("is_current")]

            if current:
                cur = current[0]
                reasons.append(
                    f"Currently {cur.get('title', 'employed')} at {cur.get('company', 'a company')} "
                    f"({cur.get('duration_months', 0)} months in role)."
                )

            if years > 0:
                num_roles = len(career)
                avg_tenure = round(total_months / num_roles / 12.0, 1) if num_roles else 0
                reasons.append(
                    f"{years} years across {num_roles} role{'s' if num_roles != 1 else ''} "
                    f"(avg tenure {avg_tenure}yr)."
                )

            # Check for product-company vs services background
            service_count = 0
            product_companies = []
            for c in career:
                comp = c.get("company", "").lower()
                if any(sc in comp for sc in SERVICE_COMPANIES):
                    service_count += 1
                else:
                    product_companies.append(c.get("company", ""))

            if service_count == len(career) and len(career) > 0:
                reasons.append(
                    "Entire career at IT services/consulting firms."
                )
            elif product_companies:
                unique = list(dict.fromkeys(product_companies))[:3]
                reasons.append(
                    f"Product-company experience at {', '.join(unique)}."
                )

        # ── 2. Relevant skills (DYNAMIC — matched against JD text) ────
        skill_names = [s.get("name", "") for s in skills]
        if jd_words:
            # A skill is "JD-relevant" if ANY word in the skill name appears in the JD
            jd_matches = []
            for s_name in skill_names:
                s_words = set(s_name.lower().split())
                # Match if skill name (or any word in it) is found in the JD
                if s_words & jd_words or s_name.lower() in jd_text.lower():
                    jd_matches.append(s_name)
            if jd_matches:
                display = jd_matches[:6]
                reasons.append(
                    f"JD-relevant skills: {', '.join(display)}"
                    + (f" (+{len(jd_matches) - 6} more)" if len(jd_matches) > 6 else "")
                    + "."
                )

        # Expert skills
        expert_skills = [
            s.get("name", "")
            for s in skills
            if s.get("proficiency", "").lower() == "expert" and s.get("duration_months", 0) > 24
        ]
        if expert_skills:
            display = expert_skills[:4]
            reasons.append(
                f"Expert-level (24+ months) in {', '.join(display)}"
                + (f" and {len(expert_skills) - 4} more" if len(expert_skills) > 4 else "")
                + "."
            )

        # ── 3. Scoring highlights ─────────────────────────────────────
        sem = scores.get("semantic_fit", 0)
        jrf = scores.get("jd_requirement_fit", 0)
        ri = scores.get("retrieval_intelligence", 0)
        pr = scores.get("production_readiness", 0)
        st = scores.get("skill_trust", 0)
        bi = scores.get("behavioral_intelligence", 0)
        cq = scores.get("career_quality", 0)
        cs = scores.get("consistency", 0)
        edu = scores.get("education", 0)

        # Find the strongest and weakest dimensions
        dims = {
            "Semantic fit": sem,
            "JD requirement coverage": jrf,
            "Retrieval intelligence": ri,
            "Production readiness": pr,
            "Skill trust": st,
            "Behavioral signals": bi,
            "Career quality": cq,
            "Consistency": cs,
            "Education": edu,
        }
        strongest = max(dims, key=dims.get)
        weakest = min(dims, key=dims.get)

        if dims[strongest] > 60:
            reasons.append(f"Strongest signal: {strongest} ({dims[strongest]}/100).")

        if dims[weakest] < 40:
            reasons.append(f"Weakest area: {weakest} ({dims[weakest]}/100).")

        # ── 4. Behavioral signals ─────────────────────────────────────
        rr = signals.get("recruiter_response_rate", 0)
        last_active = signals.get("last_active_date", "")
        notice = signals.get("notice_period_days", 0)
        github = signals.get("github_activity_score", -1)
        open_to_work = signals.get("open_to_work_flag", False)

        # Activity & availability
        if last_active:
            try:
                la_date = datetime.datetime.strptime(last_active[:10], "%Y-%m-%d").date()
                days_inactive = (REFERENCE_DATE - la_date).days
                if days_inactive <= 7:
                    reasons.append("Active on Redrob in the last week — highly reachable.")
                elif days_inactive <= 30:
                    reasons.append(f"Last active {days_inactive} days ago — recently engaged.")
                elif days_inactive > BEHAVIORAL_CONFIG["inactivity_hard_penalty_days"]:
                    reasons.append(
                        f"Inactive for {days_inactive} days — may no longer be in the market."
                    )
            except ValueError:
                pass

        if open_to_work:
            reasons.append("Marked 'Open to Work' on platform.")

        if rr >= 0.8:
            reasons.append(f"Recruiter response rate {rr:.0%} — highly responsive.")
        elif rr < 0.2 and rr >= 0:
            reasons.append(f"Low recruiter response rate ({rr:.0%}) — may be hard to engage.")

        if notice <= 30 and notice > 0:
            reasons.append(f"Notice period {notice} days — can join quickly.")
        elif notice > 90:
            reasons.append(f"Notice period {notice} days — longer onboarding lead time.")

        if github >= BEHAVIORAL_CONFIG["github_score_strong"]:
            reasons.append(f"Strong GitHub activity (score {github}/100) — external validation of work.")
        elif github >= BEHAVIORAL_CONFIG["github_score_moderate"]:
            reasons.append(f"Moderate GitHub activity (score {github}/100).")

        # ── 5. Experience band fit (DYNAMIC — parsed from JD) ─────────
        if years > 0 and (exp_min > 0 or exp_max < 99):
            if exp_min <= years <= exp_max:
                reasons.append(f"Experience ({years}yr) falls within the JD's {exp_min:.0f}-{exp_max:.0f}yr band.")
            elif years < exp_min:
                reasons.append(f"Experience ({years}yr) is below the JD's minimum of {exp_min:.0f}yr.")
            elif years > exp_max:
                reasons.append(f"Experience ({years}yr) exceeds the JD's upper bound of {exp_max:.0f}yr — may be overqualified.")

        # ── 6. Penalties ──────────────────────────────────────────────
        hp = scores.get("honeypot_penalty", 0)
        rp = scores.get("role_penalty", 0)
        if hp > 0:
            reasons.append(
                f"Honeypot detector flagged this profile (penalty −{hp}). "
                "Possible timeline inconsistencies or impossible skill claims."
            )
        if rp > 0:
            reasons.append(
                f"Role alignment penalty applied (−{rp}). "
                "Possible job-family mismatch or disqualifier triggered."
            )

        # ── 7. Assessments ────────────────────────────────────────────
        assessments = signals.get("skill_assessment_scores", {})
        if assessments:
            top_assessed = sorted(assessments.items(), key=lambda x: x[1], reverse=True)[:3]
            parts = [f"{name}: {score}/100" for name, score in top_assessed]
            reasons.append(f"Platform assessments: {', '.join(parts)}.")

        # ── 8. Predictive Technical Assessment Copilot (USP) ──────────
        if blindspot and "blindspots" in blindspot:
            missing = blindspot["blindspots"]
            if missing and blindspot.get("is_hidden_gem"):
                reasons.append(f"Technical Copilot: Strong candidate but missing {', '.join(missing[:2])}. Ask: 'Can you describe how your existing skills map to {missing[0]}?'")
            elif missing:
                reasons.append(f"Technical Copilot: Gap identified in {', '.join(missing[:2])}. Ask: 'Have you had exposure to {missing[0]} in your past roles?'")
        return reasons

    def generate_explainable_summary(self, rank: int, candidate: dict) -> str:
        """
        Generate a cohesive, plain-English summary explaining the absolute 'why'
        for the candidate's ranking position. Example: 'Ranked #2 because of strong
        domain depth (9.1/10) but relocation risk (4/10) since no prior cross-city moves.'
        """
        scores = candidate.get("scores", {})
        
        # Dimensions excluding final_score and penalties
        dims = {
            "semantic matching": scores.get("semantic_fit", 0),
            "JD requirement coverage": scores.get("jd_requirement_fit", 0),
            "retrieval intelligence": scores.get("retrieval_intelligence", 0),
            "production readiness": scores.get("production_readiness", 0),
            "skill trust": scores.get("skill_trust", 0),
            "behavioral signals": scores.get("behavioral_intelligence", 0),
            "career quality": scores.get("career_quality", 0),
            "profile consistency": scores.get("consistency", 0),
            "education": scores.get("education", 0)
        }
        
        strongest_name = max(dims, key=dims.get)
        strongest_val = dims[strongest_name]
        
        weakest_name = min(dims, key=dims.get)
        weakest_val = dims[weakest_name]
        
        reason = ""
        if "semantic" in weakest_name:
            reason = "general phrasing mismatch with the JD"
        elif "JD requirement" in weakest_name:
            reason = "missing specific tools or certifications"
        elif "retrieval" in weakest_name:
            reason = "limited search/ranking depth"
        elif "production" in weakest_name:
            reason = "limited high-scale deployment experience"
        elif "skill trust" in weakest_name:
            reason = "insufficient validation of claims"
        elif "behavioral" in weakest_name:
            reason = "low recruiter response rate or recent inactivity"
        elif "career" in weakest_name:
            reason = "shorter tenures or entirely IT services background"
        elif "consistency" in weakest_name:
            reason = "mismatched title vs project history"
        elif "education" in weakest_name:
            reason = "lacking elite pedigree"
        
        # Format values natively out of 10 for the summary
        str_val = round(strongest_val / 10.0, 1)
        weak_val = round(weakest_val / 10.0, 1)
        
        return f"💡 Ranked #{rank} because of strong {strongest_name} ({str_val}/10) but lower {weakest_name} ({weak_val}/10) since {reason}."
