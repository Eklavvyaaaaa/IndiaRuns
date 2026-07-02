# Candidate Intelligence 

> **AI-native candidate ranking engine** — built for the Redrob AI × Hack2skill Hackathon, Track 1: Data & AI Challenge

---

## What It Does

Candidate Intelligence takes a raw job description and up to **100,000 candidate profiles** and delivers a ranked shortlist of the **top 100 best-fit candidates in under 300 seconds**. It doesn't filter — it *intelligently ranks*, using semantic understanding, career signal modeling, behavioral data, and active anti-gaming defenses.

---

## Key Features

🧠 Adaptive JD Parsing
Breaks down any job description into five structured signals — hard skills, soft skills, seniority level, domain context, and priority weights (must-haves vs. nice-to-haves). Scoring weights are dynamically configured per JD, not one-size-fits-all.

🔍 Semantic Skill Clustering
Goes beyond keyword matching. Related technologies are grouped into semantic clusters so candidates aren't penalized for terminology mismatches — PyTorch, TensorFlow, and "deep learning frameworks" are understood as equivalent competencies.

📈 Career Velocity Scoring
Models candidate *trajectory*, not just current state. Rapid progression is rewarded; stagnation is penalized — two candidates with identical current profiles are ranked differently based on how they got there.

📡 Behavioral Signal Integration
Activity signals — open-to-work status, profile recency, notice period, recruiter responsiveness — act as multipliers on the base score. A highly qualified but disengaged candidate can be outranked by a slightly less qualified but actively available one.

### 🛡️ Anti-Gaming Detection
Detects LLM-generated descriptions, keyword-stuffed profiles, and artificially inflated candidates using linguistic pattern analysis. Flagged profiles receive a hard penalty before ranking. Honeypot synthetic profiles are injected to continuously validate integrity.

### 💬 Explainable AI Layer
Every ranked candidate comes with candidate-specific reasoning — not a black-box score, not a generic template. Every justification maps to a verified signal that was actually computed, making hallucination structurally impossible and the shortlist fully auditable.

---

## Pipeline Overview

```
JD Input
   ↓
Adaptive JD Parser          → Extracts skills, seniority, domain, weights
   ↓
Candidate Pool (pre-loaded) → 100K profiles, zero I/O at query time
   ↓
ANN Retrieval               → Fast approximate nearest-neighbor filtering
   ↓
Multi-Signal Scoring        → Semantic + Experience + Behavioral
   ↓
Anti-Gaming Penalty         → Flag, penalise, sweep
   ↓
LambdaMART Re-Ranking       → Relative ranking, NDCG-optimised
   ↓
Top 100 Output              → Ranked · Scored · Explained
```

---

## Scoring Formula

```
base_score  = (0.45 × semantic) + (0.35 × experience) + (0.20 × behavioral)
final_score = base_score × behavioral_multiplier − anti_gaming_penalty
```

The behavioral multiplier ranges from **0.5 to 1.2** — ensuring the shortlist is both qualified *and* actionable.

---

## Evaluation Metrics

| Metric | Weight | What It Measures |
|---|---|---|
| NDCG@10 | 50% | Quality of the very top candidates |
| NDCG@50 | 30% | Quality of the broader shortlist |
| MAP | 15% | Precision across all relevant candidates |
| P@10 | 5% | Raw precision in the top 10 |

**Composite Score** = `0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10`

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Embeddings | Sentence Transformers | Semantic meaning, not keyword frequency |
| Ranking Model | LightGBM / LambdaMART | Directly optimises for NDCG |
| Vector Search | FAISS | Millisecond ANN search at 100K scale |
| Data Processing | Pandas + NumPy | Vectorised ops across full candidate pool |
| Data Format | Parquet | Faster load than CSV at 100K rows |
| Backend API | FastAPI | Async, minimal boilerplate |
| Frontend | React + TypeScript | Type-safe result schema |
| Styling | Tailwind CSS | Rapid UI under hackathon time constraints |

---

## Repo Structure

```
IndiaRuns/
├── backend/
│   ├── app/
│   │   └── ranking/
│   │       └── engine.py       ← RankingEngine core
│   ├── ground_truth.json       ← Proxy relevance labels
│   └── artifacts/              ← Pretrained model weights
├── frontend/                   ← React + TypeScript UI
├── src/                        ← Additional source files
├── legacy_v1/                  ← Previous iteration
├── evaluate.py                 ← Evaluation harness
└── submission.csv              ← Final ranked output


**Team Dev Dynasty
Track 1: Data & AI Challenge
