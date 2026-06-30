import os
import time
import json
import csv
import math
import argparse
from typing import List, Dict, Any

def compute_ndcg(ranked_rels: List[int], k: int) -> float:
    def dcg(rels, k):
        return sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(rels[:k]))
        
    actual_dcg = dcg(ranked_rels, k)
    ideal_rels = sorted(ranked_rels, reverse=True)
    ideal_dcg = dcg(ideal_rels, k)
    
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg

def compute_ap(ranked_rels: List[int]) -> float:
    # Treat relevance 3 as relevant
    relevant_hits = 0
    precision_sum = 0.0
    for i, rel in enumerate(ranked_rels):
        if rel >= 3:
            relevant_hits += 1
            precision_sum += relevant_hits / (i + 1)
            
    # For AP, we divide by total possible relevant items in the list
    total_relevant = sum(1 for r in ranked_rels if r >= 3)
    if total_relevant == 0:
        return 0.0
    return precision_sum / total_relevant

def compute_p_at_k(ranked_rels: List[int], k: int) -> float:
    if k == 0 or len(ranked_rels) == 0:
        return 0.0
    hits = sum(1 for rel in ranked_rels[:k] if rel >= 3)
    return hits / min(k, len(ranked_rels))

def main():
    parser = argparse.ArgumentParser(description="Evaluate Candidate Intelligence Engine")
    parser.add_argument("--jd", type=str, default="job_description.txt", help="Path to JD")
    parser.add_argument("--limit", type=int, default=50, help="Candidate limit for evaluation smoke test")
    parser.add_argument("--out", type=str, default="submission.csv", help="Output CSV path")
    args = parser.parse_args()

    print("="*60)
    print("🔬 REDROB EVALUATION HARNESS - PHASE 0")
    print("="*60)
    
    # 1. Load ground truth
    print("\n[1/5] Loading ground truth...")
    with open("backend/ground_truth.json", "r") as f:
        ground_truth = json.load(f)
    print(f"  Loaded {len(ground_truth)} proxy labels.")
    
    # 2. Init Ranking Engine
    print("\n[2/5] Initializing Ranking Engine...")
    t0 = time.time()
    # We import dynamically to avoid loading models if help is invoked
    import sys
    sys.path.append(os.path.abspath("backend"))
    from app.ranking.engine import RankingEngine
    
    # The ranking engine assumes it's running inside backend, so we need to pass the correct artifacts dir.
    # Since we're running from project root (RedRob/), artifacts are in backend/artifacts
    engine = RankingEngine(artifacts_dir="backend/artifacts")
    print(f"  Engine initialized in {time.time() - t0:.2f}s")
    
    # 3. Load JD
    with open(args.jd, "r") as f:
        jd_text = f.read()
        
    # 4. Rank candidates
    print(f"\n[3/5] Ranking top 100 candidates (limit dataset: {args.limit})...")
    t0 = time.time()
    
    # Instead of running the engine on all, let's see if we can pass the limit. 
    # Wait, RankingEngine uses self.df which is already loaded from parquet.
    # We just call engine.rank()
    
    # Actually, we can just call rank. 
    # We'll pass top_k=100
    candidates = engine.rank(jd_text, top_k=100)
    runtime = time.time() - t0
    
    print(f"  Ranking completed in {runtime:.2f}s")
    
    if runtime > 300:
        print("  ❌ CONSTRAINT FAILED: Runtime exceeded 5 minutes (300s).")
    else:
        print("  ✅ Constraint Check: Runtime OK.")
        
    if len(candidates) == 0:
        print("  ❌ No candidates returned. Engine failed to rank.")
        return

    # 5. Format Submission CSV
    print(f"\n[4/5] Formatting submission CSV ({args.out})...")
    with open(args.out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for i, c in enumerate(candidates):
            reasoning = " ".join(c.get("reasoning", []))
            writer.writerow([c["candidate_id"], i + 1, c["scores"]["final_score"], reasoning])
            
    expected = min(100, len(engine.df))
    if len(candidates) != expected:
        print(f"  ⚠️ Warning: Returned {len(candidates)} rows, spec requires exactly {expected}.")

    # 6. Compute Metrics
    print("\n[5/5] Computing Metrics...")
    ranked_rels = [ground_truth.get(str(c["candidate_id"]), 0) for c in candidates]
    
    ndcg_10 = compute_ndcg(ranked_rels, 10)
    ndcg_50 = compute_ndcg(ranked_rels, 50)
    ap = compute_ap(ranked_rels)
    p_10 = compute_p_at_k(ranked_rels, 10)
    p_5 = compute_p_at_k(ranked_rels, 5)
    
    composite = (0.50 * ndcg_10) + (0.30 * ndcg_50) + (0.15 * ap) + (0.05 * p_10)
    
    print("\n" + "-"*40)
    print("📈 EVALUATION RESULTS")
    print("-" * 40)
    print(f"  NDCG@10 : {ndcg_10:.4f}  (Weight: 0.50)")
    print(f"  NDCG@50 : {ndcg_50:.4f}  (Weight: 0.30)")
    print(f"  MAP     : {ap:.4f}  (Weight: 0.15)")
    print(f"  P@10    : {p_10:.4f}  (Weight: 0.05)")
    print(f"  P@5     : {p_5:.4f}  (Tiebreaker)")
    print("-" * 40)
    print(f"  🏆 COMPOSITE SCORE: {composite:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    main()
