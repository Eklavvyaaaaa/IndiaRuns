"""
skill_graph.py — Skill co-occurrence graph for understanding skill transfer.

Builds a weighted graph from the candidate pool where:
- Nodes = unique skill names
- Edges = co-occurrence frequency (skills that appear together in profiles)

At query time, a candidate who has PyTorch but not TensorFlow still gets
partial credit if the graph shows a strong edge between them — because
the skill is transferable.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Optional

import networkx as nx
from networkx.readwrite import json_graph

from src.config import JD_RELEVANT_SKILL_NAMES


def build_skill_graph(candidates: list[dict],
                      min_edge_weight: int = 5) -> nx.Graph:
    """
    Build a weighted skill co-occurrence graph from the candidate pool.
    
    For every candidate, we look at all pairs of skills they have.
    Each co-occurrence increments the edge weight between those two skills.
    
    Args:
        candidates: List of candidate dicts
        min_edge_weight: Minimum co-occurrence count to include an edge.
                         Filters noise from rare co-occurrences.
    
    Returns:
        NetworkX Graph with skill nodes and weighted edges
    """
    print(f"  Building skill co-occurrence graph from {len(candidates)} candidates...")
    
    # Count skill co-occurrences
    cooccurrence: Counter = Counter()
    skill_freq: Counter = Counter()
    
    for candidate in candidates:
        skills = candidate.get("skills", [])
        skill_names = list(set(
            s.get("name", "").lower().strip()
            for s in skills
            if s.get("name", "").strip()
        ))
        
        # Count individual skill frequency
        for name in skill_names:
            skill_freq[name] += 1
        
        # Count pairwise co-occurrences
        for i in range(len(skill_names)):
            for j in range(i + 1, len(skill_names)):
                pair = tuple(sorted([skill_names[i], skill_names[j]]))
                cooccurrence[pair] += 1
    
    # Build the graph
    G = nx.Graph()
    
    # Add nodes with frequency as attribute
    for skill, freq in skill_freq.items():
        G.add_node(skill, frequency=freq)
    
    # Add edges with weight = co-occurrence count
    edges_added = 0
    for (skill_a, skill_b), count in cooccurrence.items():
        if count >= min_edge_weight:
            # Normalize weight by the minimum frequency of either skill
            # This gives a "conditional probability" feel
            min_freq = min(skill_freq[skill_a], skill_freq[skill_b])
            normalized_weight = count / min_freq if min_freq > 0 else 0
            
            G.add_edge(skill_a, skill_b,
                       weight=count,
                       normalized_weight=normalized_weight)
            edges_added += 1
    
    print(f"  Graph built: {G.number_of_nodes()} skills, {edges_added} edges "
          f"(min_edge_weight={min_edge_weight})")
    
    return G


def get_jd_skills() -> list[str]:
    """
    Return the list of skills the JD explicitly requires or prefers.
    These are used as the target set for skill transfer scoring.
    """
    # Core skills from the JD analysis (lowercased)
    return [
        # Must-haves
        "embeddings", "sentence-transformers", "sentence transformers",
        "vector database", "pinecone", "weaviate", "qdrant", "milvus",
        "faiss", "elasticsearch", "opensearch",
        "python",
        "ranking", "retrieval", "search", "recommendation systems",
        "evaluation", "ndcg", "a/b testing",
        # Strong signals
        "pytorch", "tensorflow", "deep learning", "machine learning",
        "nlp", "natural language processing",
        "rag", "retrieval augmented generation",
        # Nice-to-haves
        "lora", "qlora", "peft", "fine-tuning llms",
        "xgboost", "learning to rank",
        "docker", "kubernetes",
        "aws", "gcp",
    ]


def score_skill_transfer(candidate_skills: list[str],
                         jd_skills: list[str],
                         graph: nx.Graph,
                         max_hops: int = 2) -> float:
    """
    Score how well a candidate's skills transfer to the JD requirements
    using the co-occurrence graph.
    
    For each JD skill the candidate doesn't have directly:
    - Check if any of their skills are graph-neighbors of the JD skill
    - If so, give partial credit based on edge weight
    
    Args:
        candidate_skills: List of candidate's skill names (lowercased)
        jd_skills: List of JD-required skill names (lowercased)
        graph: Skill co-occurrence graph
        max_hops: Maximum graph distance to consider for transfer (default 2)
    
    Returns:
        Score 0.0-1.0 representing skill transferability
    """
    if not jd_skills:
        return 0.5  # No JD skills to compare against
    
    candidate_skill_set = set(candidate_skills)
    
    direct_matches = 0
    transfer_score = 0.0
    total_jd_skills = 0
    
    for jd_skill in jd_skills:
        total_jd_skills += 1
        if jd_skill not in graph:
            continue  # Skip skills not in the graph
        
        # Direct match
        if jd_skill in candidate_skill_set:
            direct_matches += 1
            transfer_score += 1.0
            continue
        
        # Check for transferable skills (1-hop neighbors)
        best_transfer = 0.0
        if graph.has_node(jd_skill):
            for neighbor in graph.neighbors(jd_skill):
                if neighbor in candidate_skill_set:
                    edge_data = graph[jd_skill][neighbor]
                    # Use normalized weight as transfer strength (0–1)
                    weight = edge_data.get("normalized_weight", 0.0)
                    best_transfer = max(best_transfer, weight * 0.6)  # Cap at 60% credit
            
            # 2-hop check (weaker signal)
            if best_transfer < 0.1 and max_hops >= 2:
                for neighbor in graph.neighbors(jd_skill):
                    for neighbor2 in graph.neighbors(neighbor):
                        if neighbor2 in candidate_skill_set:
                            edge1 = graph[jd_skill][neighbor].get("normalized_weight", 0)
                            edge2 = graph[neighbor][neighbor2].get("normalized_weight", 0)
                            two_hop = edge1 * edge2 * 0.3  # Much weaker — cap at 30%
                            best_transfer = max(best_transfer, two_hop)
        
        transfer_score += best_transfer
    
    if total_jd_skills == 0:
        return 0.5  # No JD skills found in graph
    
    return min(1.0, transfer_score / total_jd_skills)


def get_related_skills(skill_name: str, graph: nx.Graph, top_n: int = 10) -> list[tuple[str, float]]:
    """
    Get the most related skills to a given skill from the co-occurrence graph.
    
    Useful for debugging and reasoning generation.
    
    Args:
        skill_name: Name of the skill to look up (lowercased)
        graph: Skill co-occurrence graph
        top_n: Number of related skills to return
    
    Returns:
        List of (skill_name, weight) tuples, sorted by weight descending
    """
    skill_lower = skill_name.lower().strip()
    
    if not graph.has_node(skill_lower):
        return []
    
    neighbors = []
    for neighbor in graph.neighbors(skill_lower):
        weight = graph[skill_lower][neighbor].get("normalized_weight", 0)
        neighbors.append((neighbor, weight))
    
    neighbors.sort(key=lambda x: -x[1])
    return neighbors[:top_n]


# ═══════════════════════════════════════════════════════════════════════════════
# Artifact save/load
# ═══════════════════════════════════════════════════════════════════════════════

def save_skill_graph(graph: nx.Graph, path: str) -> None:
    """Save the skill graph to a JSON file."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    data = json_graph.node_link_data(graph)
    with open(filepath, "w") as f:
        json.dump(data, f)
    size_kb = filepath.stat().st_size / 1024
    print(f"  Saved skill graph to {filepath} ({size_kb:.0f} KB)")


def load_skill_graph(path: str) -> nx.Graph:
    """Load the skill graph from a JSON file."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Skill graph file not found: {path}")
    
    with open(filepath, "r") as f:
        data = json.load(f)
    graph = json_graph.node_link_graph(data)
    
    print(f"  Loaded skill graph: {graph.number_of_nodes()} nodes, "
          f"{graph.number_of_edges()} edges")
    return graph


# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from src.data_loader import load_candidates_batch
    
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_candidates.json"
    candidates = load_candidates_batch(path)
    
    # Build graph
    graph = build_skill_graph(candidates, min_edge_weight=2)
    
    # Show some stats
    print("\nGraph stats:")
    print(f"  Nodes (unique skills): {graph.number_of_nodes()}")
    print(f"  Edges (co-occurrences): {graph.number_of_edges()}")
    
    # Show top skills by frequency
    skills_by_freq = sorted(
        graph.nodes(data=True),
        key=lambda x: x[1].get("frequency", 0),
        reverse=True
    )[:15]
    print("\nTop 15 skills by frequency:")
    for skill, data in skills_by_freq:
        print(f"  {skill}: {data.get('frequency', 0)} candidates")
    
    # Show related skills for a few JD-relevant skills
    test_skills = ["pytorch", "python", "faiss", "rag"]
    for skill in test_skills:
        related = get_related_skills(skill, graph, top_n=5)
        if related:
            print(f"\nRelated to '{skill}':")
            for rel_skill, weight in related:
                print(f"  → {rel_skill} (weight: {weight:.3f})")
    
    # Test skill transfer scoring
    jd_skills = get_jd_skills()
    print("\nSkill transfer scores for first 5 candidates:")
    for c in candidates[:5]:
        cand_skills = [s["name"].lower().strip() for s in c.get("skills", [])]
        score = score_skill_transfer(cand_skills, jd_skills, graph)
        print(f"  {c['candidate_id']} ({c['profile']['current_title']}): {score:.3f}")
