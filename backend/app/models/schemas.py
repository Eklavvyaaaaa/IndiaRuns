from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class RankRequest(BaseModel):
    job_description: str
    top_k: int = Field(default=100, ge=1, le=1000)

class CandidateScores(BaseModel):
    final_score: float
    semantic_fit: float
    retrieval_intelligence: float
    production_readiness: float
    skill_trust: float
    behavioral_intelligence: float
    career_quality: float
    consistency: float
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
    candidates: List[RankedCandidate]
