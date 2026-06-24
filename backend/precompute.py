import os
import json
import argparse
import pickle
import numpy as np
import polars as pl
import faiss
from sentence_transformers import SentenceTransformer
import networkx as nx

def build_candidate_text(row):
    """
    Builds the text document to be embedded for a candidate.
    Combining headline, summary, skills, career history, and education.
    """
    profile = row.get("profile", {})
    headline = profile.get("headline", "")
    summary = profile.get("summary", "")
    
    skills = [s.get("name", "") for s in row.get("skills", [])]
    skill_text = ", ".join(skills)
    
    career_texts = []
    for role in row.get("career_history", []):
        company = role.get("company", "")
        title = role.get("title", "")
        desc = role.get("description", "")
        career_texts.append(f"{title} at {company}. {desc}")
    career_text = " ".join(career_texts)
    
    edu_texts = []
    for edu in row.get("education", []):
        deg = edu.get("degree", "")
        field = edu.get("field_of_study", "")
        inst = edu.get("institution", "")
        edu_texts.append(f"{deg} in {field} from {inst}")
    edu_text = " ".join(edu_texts)
    
    return f"{headline}. {summary} Skills: {skill_text}. Experience: {career_text}. Education: {edu_text}"

def build_skill_graph(candidates_list):
    """
    Builds a skill co-occurrence graph using NetworkX.
    """
    G = nx.Graph()
    for row in candidates_list:
        skills = [s.get("name") for s in row.get("skills", []) if s.get("name")]
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                s1, s2 = sorted([skills[i], skills[j]])
                if G.has_edge(s1, s2):
                    G[s1][s2]['weight'] += 1
                else:
                    G.add_edge(s1, s2, weight=1)
    return G

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="../candidates.jsonl", help="Path to candidates data")
    parser.add_argument("--out-dir", type=str, default="artifacts", help="Output directory for artifacts")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of candidates processed")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    print(f"Loading data from {args.data}...")
    # Because JSON can be deeply nested and messy in NDJSON format, 
    # we'll read it natively with Python json first, then convert what we need to Polars.
    # Check if file is .json or .jsonl
    candidates_list = []
    if args.data.endswith(".jsonl"):
        with open(args.data, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    candidates_list.append(json.loads(line))
                    if args.limit and len(candidates_list) >= args.limit:
                        break
    else:
        with open(args.data, "r", encoding="utf-8") as f:
            candidates_list = json.load(f)
            if args.limit:
                candidates_list = candidates_list[:args.limit]
            
    if not isinstance(candidates_list, list):
        raise TypeError(f"Data format error: Expected a top-level JSON list in {args.data}, but got {type(candidates_list).__name__}.")
        
    if not candidates_list:
        raise ValueError(f"No candidates loaded from {args.data}. Please check the file contents.")
            
    print(f"Loaded {len(candidates_list)} candidates.")
    
    # 1. Build Texts
    print("Building candidate text for embeddings...")
    texts = [build_candidate_text(c) for c in candidates_list]
    
    # 2. Embeddings
    print("Generating embeddings using BAAI/bge-small-en-v1.5...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    # Normalize embeddings for cosine similarity via inner product
    embeddings = model.encode(texts, batch_size=256, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings).astype("float32")
    
    emb_path = os.path.join(args.out_dir, "embeddings.npy")
    np.save(emb_path, embeddings)
    print(f"Saved embeddings to {emb_path}")
    
    # 3. FAISS Index
    print("Building FAISS index...")
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d) # Inner product for cosine similarity (since embeddings are normalized)
    index.add(embeddings)
    
    faiss_path = os.path.join(args.out_dir, "faiss.index")
    faiss.write_index(index, faiss_path)
    print(f"Saved FAISS index to {faiss_path}")
    
    # 4. Parquet Features using Polars
    print("Generating features dataframe...")
    features_list = []
    for c in candidates_list:
        features_list.append({
            "candidate_id": str(c.get("candidate_id", "")),
            "anonymized_name": c.get("profile", {}).get("anonymized_name", ""),
            "title": c.get("profile", {}).get("current_title", ""),
            "summary": c.get("profile", {}).get("summary", ""),
            "skills": json.dumps(c.get("skills", [])),
            "career_history": json.dumps(c.get("career_history", [])),
            "education": json.dumps(c.get("education", [])),
            "behavioral_signals": json.dumps(c.get("redrob_signals", {}))
        })
    
    df = pl.DataFrame(features_list)
    parquet_path = os.path.join(args.out_dir, "candidate_features.parquet")
    df.write_parquet(parquet_path)
    print(f"Saved features to {parquet_path}")
    
    # 5. Skill Graph
    print("Building skill graph...")
    G = build_skill_graph(candidates_list)
    graph_path = os.path.join(args.out_dir, "skill_graph.pkl")
    with open(graph_path, "wb") as f:
        pickle.dump(G, f)
    print(f"Saved skill graph to {graph_path}")
    
    print("Precomputation complete!")

if __name__ == "__main__":
    main()
