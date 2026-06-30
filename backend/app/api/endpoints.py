from fastapi import APIRouter, Depends
import time
import os
import threading

from app.models.schemas import RankRequest, RankResponse
from app.ranking.engine import RankingEngine

router = APIRouter()

# Global engine instance to hold FAISS and Parquet in memory
engine_instance = None
_engine_lock = threading.Lock()

def get_engine():
    global engine_instance
    if engine_instance is None:
        with _engine_lock:
            if engine_instance is None:  # double-check after acquiring lock
                # Try multiple paths to find the artifacts directory
                artifacts_dir = os.getenv("ARTIFACTS_DIR", None)
                if artifacts_dir is None:
                    # Auto-detect: try common locations
                    candidates_paths = [
                        os.path.join(os.path.dirname(__file__), "../../artifacts"),  # relative to this file
                        "backend/artifacts",  # when run from project root
                        "artifacts",  # when run from backend/
                    ]
                    for p in candidates_paths:
                        if os.path.isdir(p):
                            artifacts_dir = p
                            break
                    if artifacts_dir is None:
                        artifacts_dir = candidates_paths[0]  # fallback
                engine_instance = RankingEngine(artifacts_dir)
    return engine_instance

@router.post("/rank", response_model=RankResponse)
def rank_candidates(request: RankRequest, engine: RankingEngine = Depends(get_engine)):
    start_time = time.time()
    jd_analysis = engine.build_jd_analysis(
        request.job_description,
        use_adaptive=request.use_adaptive,
        priority_overrides=request.priority_overrides,
    )
    candidates = engine.rank(
        request.job_description,
        top_k=request.top_k,
        use_adaptive=request.use_adaptive,
        priority_overrides=request.priority_overrides,
        jd_analysis=jd_analysis,
    )
    
    processing_time = (time.time() - start_time) * 1000.0
    
    return RankResponse(
        status="success",
        processing_time_ms=round(processing_time, 2),
        jd_analysis=jd_analysis,
        candidates=candidates
    )
