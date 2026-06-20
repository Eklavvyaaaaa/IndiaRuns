"""
semantic.py — Sentence-transformer embeddings and cosine similarity.

Handles embedding generation (pre-computation phase) and similarity
computation (ranking phase). The model is only loaded during pre-computation;
at ranking time we just do numpy math on pre-computed vectors.
"""

import numpy as np
from pathlib import Path
from typing import Optional

from src.config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL_NAME, SEMANTIC_TOP_K


def load_model(model_name: str = EMBEDDING_MODEL_NAME):
    """
    Load the sentence-transformer model.
    
    Only needed during pre-computation — ranking uses pre-computed embeddings.
    
    Args:
        model_name: HuggingFace model name (default: all-MiniLM-L6-v2)
        
    Returns:
        SentenceTransformer model instance
    """
    from sentence_transformers import SentenceTransformer
    
    print(f"  Loading sentence-transformer model: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"  Model loaded. Embedding dimension: {model.get_embedding_dimension()}")
    return model


def embed_texts(model, texts: list[str], batch_size: int = EMBEDDING_BATCH_SIZE,
                show_progress: bool = True) -> np.ndarray:
    """
    Encode a list of texts into embeddings using the sentence-transformer model.
    
    Args:
        model: SentenceTransformer model instance
        texts: List of text strings to embed
        batch_size: Batch size for encoding (larger = faster but more memory)
        show_progress: Whether to show a progress bar
        
    Returns:
        numpy array of shape (len(texts), embedding_dim), dtype float32
    """
    print(f"  Embedding {len(texts)} texts (batch_size={batch_size})...")
    
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True,  # L2 normalize — cosine sim becomes dot product
    )
    
    print(f"  Embeddings shape: {embeddings.shape}")
    return embeddings.astype(np.float32)


def embed_jd(model, jd_text: str) -> np.ndarray:
    """
    Embed the job description text into a single vector.
    
    Args:
        model: SentenceTransformer model instance
        jd_text: Full JD text
        
    Returns:
        1-D numpy array of shape (embedding_dim,)
    """
    # For the JD, we want to capture the key requirements, not the fluff.
    # Extract the most relevant sections.
    jd_embedding = model.encode(
        [jd_text],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return jd_embedding[0].astype(np.float32)


def compute_semantic_scores(candidate_embeddings: np.ndarray,
                            jd_embedding: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between all candidate embeddings and the JD embedding.
    
    Since embeddings are L2-normalized, cosine similarity = dot product.
    This is very fast — ~2 seconds for 100K × 384 on CPU.
    
    Args:
        candidate_embeddings: (N, D) array of candidate embeddings
        jd_embedding: (D,) array of JD embedding
        
    Returns:
        (N,) array of cosine similarity scores in [-1, 1]
    """
    # Dot product on normalized vectors = cosine similarity
    scores = candidate_embeddings @ jd_embedding
    return scores


def get_top_k_indices(scores: np.ndarray, k: int = SEMANTIC_TOP_K) -> np.ndarray:
    """
    Get indices of the top-K candidates by semantic score.
    
    Uses numpy argpartition for O(N) selection instead of O(N log N) full sort.
    
    Args:
        scores: (N,) array of similarity scores
        k: Number of top candidates to select
        
    Returns:
        (K,) array of indices, sorted by score descending
    """
    k = min(k, len(scores))
    
    # argpartition is O(N) — much faster than argsort for large N
    top_k_unsorted = np.argpartition(scores, -k)[-k:]
    
    # Sort only the top K by score descending
    top_k_sorted = top_k_unsorted[np.argsort(scores[top_k_unsorted])[::-1]]
    
    return top_k_sorted


# ═══════════════════════════════════════════════════════════════════════════════
# Artifact save/load — for the two-phase architecture
# ═══════════════════════════════════════════════════════════════════════════════

def save_embeddings(embeddings: np.ndarray, path: str) -> None:
    """Save embeddings to a .npy file."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    np.save(filepath, embeddings)
    size_mb = filepath.stat().st_size / (1024 * 1024)
    print(f"  Saved embeddings to {filepath} ({size_mb:.1f} MB)")


def load_embeddings(path: str) -> np.ndarray:
    """Load embeddings from a .npy file."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Embeddings file not found: {path}")
    
    embeddings = np.load(filepath)
    print(f"  Loaded embeddings: {embeddings.shape} from {filepath.name}")
    return embeddings


def save_jd_embedding(embedding: np.ndarray, path: str) -> None:
    """Save the JD embedding to a .npy file."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    np.save(filepath, embedding)
    print(f"  Saved JD embedding to {filepath}")


def load_jd_embedding(path: str) -> np.ndarray:
    """Load the JD embedding from a .npy file."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"JD embedding file not found: {path}")
    
    embedding = np.load(filepath)
    print(f"  Loaded JD embedding: {embedding.shape}")
    return embedding


# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from src.data_loader import load_sample_candidates
    from src.feature_extractor import extract_profile_text
    
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_candidates.json"
    candidates = load_sample_candidates(path, n=10)
    
    # Extract profile texts
    texts = [extract_profile_text(c) for c in candidates]
    
    # Load model and embed
    model = load_model()
    embeddings = embed_texts(model, texts, batch_size=32, show_progress=False)
    
    # Create a mock JD embedding (just use the first candidate's text for testing)
    jd_text = "Senior AI Engineer with experience in embeddings, retrieval, ranking, vector databases, Python, production ML systems"
    jd_emb = embed_jd(model, jd_text)
    
    # Compute scores
    scores = compute_semantic_scores(embeddings, jd_emb)
    
    # Show results
    print(f"\nSemantic similarity scores (vs mock JD):")
    for i, c in enumerate(candidates):
        cid = c["candidate_id"]
        title = c["profile"]["current_title"]
        print(f"  {cid} ({title:25s}): {scores[i]:.4f}")
    
    # Get top-K
    top_indices = get_top_k_indices(scores, k=5)
    print(f"\nTop 5 by semantic score:")
    for idx in top_indices:
        c = candidates[idx]
        print(f"  #{idx+1}: {c['candidate_id']} ({c['profile']['current_title']}) — {scores[idx]:.4f}")
