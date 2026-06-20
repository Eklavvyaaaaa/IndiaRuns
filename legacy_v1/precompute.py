"""
precompute.py — Offline computation phase for the Candidate Intelligence Engine.

Computes embeddings and builds the skill co-occurrence graph.
This runs without the 5-minute time limit.
"""

import os
import argparse
from pathlib import Path

from src.data_loader import load_candidates_batch
from src.feature_extractor import extract_profile_text
from src.semantic import load_model, embed_texts, save_embeddings
from src.skill_graph import build_skill_graph, save_skill_graph
from src.config import EMBEDDING_BATCH_SIZE

def main():
    parser = argparse.ArgumentParser(description="Precompute candidate intelligence artifacts.")
    parser.add_argument("--data", type=str, default="candidates.jsonl", help="Path to candidates data")
    parser.add_argument("--out-dir", type=str, default="artifacts", help="Output directory for artifacts")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of candidates for testing")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🚀 REDROB CANDIDATE INTELLIGENCE ENGINE - PRECOMPUTATION")
    print("="*60 + "\n")
    
    # 1. Load data
    print("[1/4] Loading candidate data...")
    candidates = load_candidates_batch(args.data)
    if args.limit:
        candidates = candidates[:args.limit]
    print(f"  Loaded {len(candidates)} candidates.")
    
    # 2. Build and save Skill Graph
    print("\n[2/4] Building skill co-occurrence graph...")
    # min_edge_weight: For 100K candidates, require at least 10 co-occurrences.
    # For smaller test samples, use 2.
    min_weight = 10 if len(candidates) > 5000 else 2
    graph = build_skill_graph(candidates, min_edge_weight=min_weight)
    
    graph_path = os.path.join(args.out_dir, "skill_graph.json")
    save_skill_graph(graph, graph_path)
    
    # 3. Extract texts for embedding
    print("\n[3/4] Extracting textual features...")
    texts = [extract_profile_text(c) for c in candidates]
    
    # 4. Generate and save embeddings
    print("\n[4/4] Generating semantic embeddings...")
    model = load_model()
    embeddings = embed_texts(model, texts, batch_size=EMBEDDING_BATCH_SIZE)
    
    emb_path = os.path.join(args.out_dir, "candidate_embeddings.npy")
    save_embeddings(embeddings, emb_path)
    
    print("\n" + "="*60)
    print(f"✅ PRECOMPUTATION COMPLETE. Artifacts saved to '{args.out_dir}/'")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
