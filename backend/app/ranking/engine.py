import polars as pl

from app.ranking.semantic import SemanticSearchLayer
from app.ranking.retrieval import RetrievalIntelligenceLayer
from app.ranking.production import ProductionReadinessLayer
from app.ranking.skill_trust import SkillTrustLayer
from app.ranking.behavioral import BehavioralIntelligenceLayer
from app.ranking.career_quality import CareerQualityLayer
from app.ranking.consistency import ConsistencyLayer
from app.ranking.role_alignment import RoleAlignmentLayer
from app.ranking.honeypot import HoneypotDetector
from app.ranking.blindspot import BlindSpotEngine
from app.ranking.reasoner import ReasoningEngine
from app.ranking.education import EducationLayer
from app.ranking.jd_adaptive import JDAdaptiveWeightEngine
from app.ranking.jd_requirement_fit import JDRequirementFitLayer

class RankingEngine:
    def __init__(self, artifacts_dir: str = "backend/artifacts"):
        self.semantic = SemanticSearchLayer(artifacts_dir)
        self.retrieval = RetrievalIntelligenceLayer()
        self.production = ProductionReadinessLayer()
        self.skill_trust = SkillTrustLayer()
        self.behavioral = BehavioralIntelligenceLayer()
        self.career_quality = CareerQualityLayer()
        self.consistency = ConsistencyLayer()
        self.education = EducationLayer()
        self.jd_adaptive = JDAdaptiveWeightEngine()
        self.jd_requirement_fit = JDRequirementFitLayer(self.semantic.model)
        self.role_alignment = RoleAlignmentLayer()
        self.honeypot = HoneypotDetector()
        self.blindspot = BlindSpotEngine()
        self.reasoner = ReasoningEngine()
        self.last_jd_analysis = None
        
        # Load candidate features
        import os
        import numpy as np
        
        parquet_path = os.path.join(artifacts_dir, "candidate_features.parquet")
        emb_path = os.path.join(artifacts_dir, "embeddings.npy")
        
        if os.path.exists(parquet_path):
            self.df = pl.read_parquet(parquet_path)
            
            # Validate embeddings match dataframe
            if os.path.exists(emb_path):
                emb_len = len(np.load(emb_path, mmap_mode='r'))
                if emb_len != len(self.df):
                    raise ValueError(f"Data corruption: Found {emb_len} embeddings but {len(self.df)} candidates in Parquet. Please re-run precompute.py.")
        else:
            self.df = None

    def build_jd_analysis(
        self,
        jd_text: str,
        use_adaptive: bool = False,
        priority_overrides: dict[str, float] | None = None,
    ) -> dict:
        if use_adaptive:
            jd_analysis = self.jd_adaptive.analyze(jd_text)
            return self.jd_adaptive.apply_priority_overrides(jd_analysis, priority_overrides)
        return self.jd_adaptive.base_analysis()

    def rank(
        self,
        jd_text: str,
        top_k: int = 100,
        use_adaptive: bool = False,
        priority_overrides: dict[str, float] | None = None,
        jd_analysis: dict | None = None,
    ) -> list[dict]:
        if self.df is None:
            return []

        if jd_analysis is None:
            jd_analysis = self.build_jd_analysis(jd_text, use_adaptive, priority_overrides)
        self.last_jd_analysis = jd_analysis
        weights = jd_analysis["adaptive_weights"]

        # 1. Semantic Search (Fetch a deep pool to ensure the engine has enough to re-rank)
        pool_size = max(1000, top_k * 5)
        semantic_matches = self.semantic.search(jd_text, top_k=pool_size)
        
        results = []
        for faiss_idx, sem_score in semantic_matches:
            # Polars is fast, we can fetch row by index 
            # Note: Assuming FAISS index matches dataframe row index exactly (1:1 mapping)
            row = self.df.row(faiss_idx, named=True)
            
            # Semantic score from FAISS (cosine sim 0 to 1 -> 0 to 100)
            semantic_fit = max(0.0, min(100.0, sem_score * 100.0))
            
            # 2. Data Integrity & Role Alignment check
            is_quarantined, hp_penalty, profile_reliability = self.honeypot.detect(row)
            
            # Compute production readiness early for role alignment disqualifiers
            pr_score = self.production.score(row)
            
            role_penalty, role_warnings = self.role_alignment.penalize(jd_text, row, pr_score)
            
            # 3. Compute other layers
            ri_score = self.retrieval.score(row)
            st_score = self.skill_trust.score(row)
            bi_score = self.behavioral.score(row)
            cq_score = self.career_quality.score(row)
            cs_score = self.consistency.score(row)
            edu_score = self.education.score(row, jd_analysis)
            jrf_score = self.jd_requirement_fit.score(jd_text, row)
            
            # Calculate weighted final score
            final_score = (
                (semantic_fit * weights["semantic"]) +
                (jrf_score * weights["jrf"]) +
                (ri_score * weights["ri"]) +
                (pr_score * weights["pr"]) +
                (st_score * weights["st"]) +
                (bi_score * weights["bi"]) +
                (cq_score * weights["cq"]) +
                (cs_score * weights["cs"]) +
                (edu_score * weights["edu"])
            ) - hp_penalty - role_penalty
            
            if is_quarantined:
                final_score = 0.0
                
            final_score = max(0.0, final_score)
            
            scores = {
                "final_score": round(final_score, 1),
                "semantic_fit": round(semantic_fit, 1),
                "jd_requirement_fit": round(jrf_score, 1),
                "retrieval_intelligence": round(ri_score, 1),
                "production_readiness": round(pr_score, 1),
                "skill_trust": round(st_score, 1),
                "behavioral_intelligence": round(bi_score, 1),
                "career_quality": round(cq_score, 1),
                "consistency": round(cs_score, 1),
                "education": round(edu_score, 1),
                "profile_reliability": round(profile_reliability * 100.0, 1),
                "honeypot_penalty": round(hp_penalty, 1),
                "role_penalty": round(role_penalty, 1)
            }
            
            # 4. Blindspot
            bs = self.blindspot.compute(jd_text, row, final_score)
            
            # 5. Reasoning
            reasons = self.reasoner.generate(row, scores, jd_text, bs)
            
            if role_warnings:
                for w in role_warnings:
                    reasons.append(f"WARNING: {w}")

            active_signals = [
                s["label"] for s in jd_analysis.get("signals", [])
                if s.get("polarity") == "positive"
            ]
            if use_adaptive and active_signals:
                reasons.append(
                    "JD-adaptive weighting active: "
                    + ", ".join(active_signals[:4])
                    + f". Education weight={weights['edu']:.2f}."
                )
            if use_adaptive and jd_analysis.get("manual_priorities"):
                reasons.append(
                    "Manual adaptive priorities active. "
                    + f"Education weight={weights['edu']:.2f}, career weight={weights['cq']:.2f}."
                )
            
            results.append({
                "candidate_id": row["candidate_id"],
                "anonymized_name": row["anonymized_name"],
                "title": row.get("title", "Candidate"),
                "summary": row.get("summary", ""),
                "scores": scores,
                "blindspot": bs,
                "reasoning": reasons,
                "is_honeypot": is_quarantined
            })
            
        # Sort by final score
        results.sort(key=lambda x: x["scores"]["final_score"], reverse=True)
        
        return results[:top_k]
