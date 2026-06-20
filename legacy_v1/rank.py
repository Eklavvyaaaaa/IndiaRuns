"""
rank.py — Fast ranking script for the Candidate Intelligence Engine.

Executes under the 5-minute CPU constraint by leveraging pre-computed
embeddings and skill graphs.
"""

import time
import argparse
import os

from src.data_loader import load_candidates_batch
from src.feature_extractor import extract_all_features, extract_skill_claims
from src.semantic import load_model, embed_jd, load_embeddings, compute_semantic_scores, get_top_k_indices
from src.skill_graph import load_skill_graph
from src.jd_adaptive import derive_weights
from src.scoring import compute_final_score
from src.reasoning import generate_reasoning
from src.config import SEMANTIC_TOP_K

def main():
    parser = argparse.ArgumentParser(description="Rank candidates against a Job Description.")
    parser.add_argument("--jd", type=str, default="job_description.txt", help="Path to JD text file")
    parser.add_argument("--data", type=str, default="candidates.jsonl", help="Path to candidates data")
    parser.add_argument("--artifacts", type=str, default="artifacts", help="Directory with precomputed artifacts")
    parser.add_argument("--top-n", type=int, default=10, help="Number of final candidates to output")
    parser.add_argument("--limit", type=int, default=None, help="Limit candidate pool (for testing)")
    args = parser.parse_args()
    
    start_time = time.time()
    print("\n" + "="*60)
    print("🎯 REDROB CANDIDATE INTELLIGENCE ENGINE - FAST RANKING")
    print("="*60 + "\n")
    
    # 1. Load JD
    with open(args.jd, "r") as f:
        jd_text = f.read()
        
    print("[1/6] Analyzing Job Description...")
    weights = derive_weights(jd_text)
    print("  Dynamically derived weights:")
    for k, v in weights.items():
        print(f"    - {k:16s}: {v:.3f}")
        
    # We also need jd_skills. We can mock this extraction or use the ones defined in config
    from src.config import JD_REQUIRED_SKILLS
    jd_skills = JD_REQUIRED_SKILLS
        
    # 2. Load Artifacts
    print("\n[2/6] Loading pre-computed artifacts...")
    t0 = time.time()
    graph_path = os.path.join(args.artifacts, "skill_graph.json")
    emb_path = os.path.join(args.artifacts, "candidate_embeddings.npy")
    
    skill_graph = load_skill_graph(graph_path)
    embeddings = load_embeddings(emb_path)
    print(f"  Artifacts loaded in {time.time() - t0:.2f}s")
    
    # 3. Load Candidates Database
    print("\n[3/6] Loading candidate metadata...")
    t0 = time.time()
    # In a real db we'd query by ID. Here we load the JSONL in memory.
    candidates = load_candidates_batch(args.data)
    if args.limit:
        candidates = candidates[:args.limit]
    print(f"  Loaded {len(candidates)} records in {time.time() - t0:.2f}s")
    
    if len(candidates) != len(embeddings):
        print(f"  ⚠️ WARNING: Candidates count ({len(candidates)}) != Embeddings count ({len(embeddings)})")
        print("  Did you run precompute.py on the same dataset?")
    
    # 4. Semantic Filtering
    print("\n[4/6] Running massive-scale semantic filter...")
    t0 = time.time()
    model = load_model()  # Loading the model takes ~2-3 seconds
    jd_emb = embed_jd(model, jd_text)
    
    scores = compute_semantic_scores(embeddings, jd_emb)
    # Get top K to pass to heavy scoring
    k = min(SEMANTIC_TOP_K, len(scores))
    top_k_idx = get_top_k_indices(scores, k=k)
    print(f"  Semantic filter matched {len(embeddings)} candidates to top {k} in {time.time() - t0:.2f}s")
    
    # 5. Deep Scoring Pipeline
    print("\n[5/6] Executing Deep Intelligence Scoring...")
    t0 = time.time()
    
    scored_candidates = []
    
    for idx in top_k_idx:
        candidate = candidates[idx]
        sem_score = scores[idx]
        
        # Extract structured features
        features = extract_all_features(candidate)
        skill_claims = extract_skill_claims(candidate)
        
        # Behavioral penalty/boost
        from src.behavioral import compute_behavioral_multiplier
        behavioral_mult = compute_behavioral_multiplier(candidate.get("signals", {}))
        
        # Honeypot check
        from src.honeypot import is_likely_honeypot
        if is_likely_honeypot(candidate):
            continue  # Drop honeypots completely
            
        # Final mathematical score
        final_score, components = compute_final_score(
            candidate=candidate,
            features=features,
            semantic_score=sem_score,
            skill_graph=skill_graph,
            weights=weights,
            jd_skills=jd_skills,
            skill_claims=skill_claims,
            behavioral_multiplier=behavioral_mult
        )
        
        scored_candidates.append((final_score, candidate, components))
        
    print(f"  Deep scoring completed in {time.time() - t0:.2f}s")
    
    # Sort by final score
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 6. Output Generation
    print("\n[6/6] Generating Fact-Based Reasoning...\n")
    print("="*60)
    print(f"🏆 TOP {args.top_n} CANDIDATES")
    print("="*60 + "\n")
    
    for rank, (score, cand, comps) in enumerate(scored_candidates[:args.top_n], start=1):
        reasoning = generate_reasoning(cand, rank, score, weights, comps, jd_skills)
        print(reasoning)
        print("-" * 60)
        
    total_time = time.time() - start_time
    print(f"\n⏱️  Total execution time: {total_time:.2f} seconds (Limit: 300.0s)")

if __name__ == "__main__":
    main()
