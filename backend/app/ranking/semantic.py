import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os

class SemanticSearchLayer:
    def __init__(self, artifacts_dir: str = "backend/artifacts"):
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        
        faiss_path = os.path.join(artifacts_dir, "faiss.index")
        if os.path.exists(faiss_path):
            self.index = faiss.read_index(faiss_path)
        else:
            self.index = None

    def search(self, jd_text: str, top_k: int = 200) -> list[tuple[int, float]]:
        """
        Embeds the Job Description and queries the FAISS index.
        Returns a list of tuples (candidate_index_in_faiss, cosine_similarity_score).
        """
        if self.index is None:
            return []
            
        query_text = f"Represent this sentence for searching relevant passages: {jd_text}"
        emb = self.model.encode([query_text], normalize_embeddings=True)
        emb = np.array(emb).astype("float32")
        
        # Search FAISS. index.search returns (distances/scores, indices)
        scores, indices = self.index.search(emb, top_k)
        
        results = []
        for i in range(len(indices[0])):
            idx = int(indices[0][i])
            score = float(scores[0][i])
            if idx != -1:
                results.append((idx, score))
                
        return results
