from pydantic import BaseModel, Field
from typing import List, Dict, Any

class RankRequest(BaseModel):
    job_description: str
    top_k: int = Field(default=100, ge=1, le=1000)
    use_adaptive: bool = False
    priority_overrides: Dict[str, float] = Field(default_factory=dict)

class CandidateScores(BaseModel):
    final_score: float
    semantic_fit: float
    jd_requirement_fit: float
    retrieval_intelligence: float
    production_readiness: float
    skill_trust: float
    behavioral_intelligence: float
    career_quality: float
    consistency: float
    education: float
    profile_reliability: float
    honeypot_penalty: float
    role_penalty: float

class BlindSpot(BaseModel):
    ats_score: float
    capability_score: float
    delta: float
    is_hidden_gem: bool

class RankedCandidate(BaseModel):
    candidate_id: str
    anonymized_name: str
    title: str
    summary: str
    scores: CandidateScores
    blindspot: BlindSpot
    reasoning: List[str]
    is_honeypot: bool

class RankResponse(BaseModel):
    status: str
    processing_time_ms: float
    jd_analysis: Dict[str, Any] = Field(default_factory=dict)
    candidates: List[RankedCandidate]
