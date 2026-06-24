"""
app.py — Streamlit UI for the Candidate Intelligence Engine.
"""
import streamlit as st
import time
import os

from src.data_loader import load_candidates_batch
from src.feature_extractor import extract_all_features, extract_skill_claims
from src.semantic import load_model, embed_jd, load_embeddings, compute_semantic_scores, get_top_k_indices
from src.skill_graph import load_skill_graph
from src.jd_adaptive import derive_weights
from src.scoring import compute_final_score
from src.reasoning import generate_reasoning
from src.config import SEMANTIC_TOP_K, JD_REQUIRED_SKILLS
from src.behavioral import compute_behavioral_multiplier
from src.honeypot import is_likely_honeypot

st.set_page_config(page_title="RedRob Candidate Engine", page_icon="🎯", layout="wide")

@st.cache_resource
def get_model():
    return load_model()

@st.cache_data
def load_all_data(data_path, artifacts_path):
    candidates = load_candidates_batch(data_path)
    emb_path = os.path.join(artifacts_path, "candidate_embeddings.npy")
    graph_path = os.path.join(artifacts_path, "skill_graph.json")
    embeddings = load_embeddings(emb_path)
    skill_graph = load_skill_graph(graph_path)
    return candidates, embeddings, skill_graph

def main():
    st.title("🎯 RedRob Candidate Intelligence Engine")
    st.markdown("""
    Rank candidates against a Job Description dynamically.
    This system evades keyword-stuffing and AI-generated CVs using temporal decay, 
    behavioral tracking, and honeypot detection.
    """)
    
    # Defaults
    data_path = "candidates.jsonl" if os.path.exists("candidates.jsonl") else "sample_candidates.json"
    artifacts_path = "artifacts"
    
    try:
        model = get_model()
        candidates, embeddings, skill_graph = load_all_data(data_path, artifacts_path)
    except Exception as e:
        st.error(f"Error loading artifacts: {e}")
        st.info("Did you run `python precompute.py` first?")
        return
        
    st.sidebar.header("Configuration")
    top_n = st.sidebar.slider("Top N Candidates", 5, 50, 10)
    
    default_jd = ""
    if os.path.exists("job_description.txt"):
        with open("job_description.txt", "r") as f:
            default_jd = f.read()
    else:
        default_jd = "We are looking for a Senior AI Engineer..."
        
    jd_text = st.text_area("Job Description", value=default_jd, height=300)
    
    if st.button("🚀 Rank Candidates", type="primary"):
        with st.spinner("Analyzing JD and running Semantic Filter..."):
            t0 = time.time()
            weights = derive_weights(jd_text)
            
            # Embed JD and get top K
            jd_emb = embed_jd(model, jd_text)
            scores = compute_semantic_scores(embeddings, jd_emb)
            k = min(SEMANTIC_TOP_K, len(scores))
            top_k_idx = get_top_k_indices(scores, k=k)
            
        with st.spinner("Executing Deep Intelligence Scoring Pipeline..."):
            scored_candidates = []
            
            for idx in top_k_idx:
                candidate = candidates[idx]
                sem_score = scores[idx]
                
                features = extract_all_features(candidate)
                skill_claims = extract_skill_claims(candidate)
                
                behavioral_mult = compute_behavioral_multiplier(candidate.get("signals", {}))
                
                if is_likely_honeypot(candidate):
                    continue  # Filter honeypots
                    
                final_score, components = compute_final_score(
                    candidate=candidate,
                    features=features,
                    semantic_score=sem_score,
                    skill_graph=skill_graph,
                    weights=weights,
                    jd_skills=JD_REQUIRED_SKILLS,
                    skill_claims=skill_claims,
                    behavioral_multiplier=behavioral_mult
                )
                
                scored_candidates.append((final_score, candidate, components))
                
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            
        st.success(f"Scored and ranked {len(scored_candidates)} candidates from an initial semantic pool of {k} in {time.time() - t0:.2f} seconds!")
        
        st.subheader("🏆 Top Ranked Candidates")
        for rank, (score, cand, comps) in enumerate(scored_candidates[:top_n], start=1):
            reasoning = generate_reasoning(cand, rank, score, weights, comps, JD_REQUIRED_SKILLS)
            
            with st.expander(f"#{rank} - {cand.get('profile', {}).get('current_title', 'Unknown')} ({score*100:.1f}/100)"):
                st.markdown(f"**Reasoning:** {reasoning}")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Semantic Fit", f"{comps['semantic_fit']*100:.0f}")
                col2.metric("Career Fit", f"{comps['career_fit']*100:.0f}")
                col3.metric("Skill Trust", f"{comps['skill_trust']*100:.0f}")
                col4.metric("Velocity", f"{comps['career_velocity']*100:.0f}")
                col5.metric("Location Fit", f"{comps['location_fit']*100:.0f}")
                
                st.write(f"**Behavioral Multiplier:** {comps['behavioral_multiplier']:.2f}")
                st.write(f"**BlindSpot Delta:** +{comps['blindspot_delta']*100:.1f} pts over traditional ATS")
                if comps['penalties'] < 0:
                    st.error(f"Penalty applied: {comps['penalties']}")

if __name__ == "__main__":
    main()
