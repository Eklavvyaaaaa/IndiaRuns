from fastapi import APIRouter, Depends
import time

from app.models.schemas import RankRequest, RankResponse
from app.ranking.engine import RankingEngine

router = APIRouter()

# Global engine instance to hold FAISS and Parquet in memory
engine_instance = None

def get_engine():
    global engine_instance
    if engine_instance is None:
        engine_instance = RankingEngine("artifacts")
    return engine_instance

@router.post("/rank", response_model=RankResponse)
def rank_candidates(request: RankRequest, engine: RankingEngine = Depends(get_engine)):
    start_time = time.time()
    
    candidates = engine.rank(request.job_description, top_k=request.top_k)
    
    processing_time = (time.time() - start_time) * 1000.0
    
    return RankResponse(
        status="success",
        processing_time_ms=round(processing_time, 2),
        candidates=candidates
    )
