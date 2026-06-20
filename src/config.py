"""
config.py — Central configuration for the Candidate Intelligence Engine.

All constants, weights, decay rates, company lists, signal keywords,
and penalty values live here. No other module should hard-code these values.
"""

from datetime import date

# ═══════════════════════════════════════════════════════════════════════════════
# Scoring dimension base weights (sum to 1.0)
# These are defaults — the JD-Adaptive Weight Engine recalibrates per JD.
# ═══════════════════════════════════════════════════════════════════════════════
BASE_WEIGHTS = {
    "semantic_fit": 0.30,
    "career_fit": 0.25,
    "skill_trust": 0.20,
    "career_velocity": 0.15,
    "location_fit": 0.10,
}

# ═══════════════════════════════════════════════════════════════════════════════
# Embedding model
# ═══════════════════════════════════════════════════════════════════════════════
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # Output dimension for all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE = 256

# Top-K candidates to pass from semantic filter to deep scoring
SEMANTIC_TOP_K = 500

# ═══════════════════════════════════════════════════════════════════════════════
# Skill half-life decay rates (λ per month)
# Half-life = ln(2) / λ
# ═══════════════════════════════════════════════════════════════════════════════
DECAY_RATES: dict[str, float] = {
    "llm_tooling": 0.090,       # half-life ~8 months  (LangChain, DSPy, CrewAI)
    "vector_retrieval": 0.060,  # half-life ~12 months (Pinecone, FAISS, Weaviate)
    "ml_frameworks": 0.030,     # half-life ~23 months (PyTorch, JAX, TF)
    "mlops_infra": 0.045,       # half-life ~15 months (MLflow, Ray, Kubeflow)
    "data_engineering": 0.035,  # half-life ~20 months (Spark, dbt, Kafka)
    "cloud_platforms": 0.025,   # half-life ~28 months (AWS SM, GCP Vertex)
    "foundational_ml": 0.010,   # half-life ~69 months (statistics, linear algebra)
    "programming_lang": 0.008,  # half-life ~87 months (Python, SQL)
}
DEFAULT_DECAY = 0.040  # Fallback for uncategorised skills

# ═══════════════════════════════════════════════════════════════════════════════
# Skill → category mapping (fuzzy keyword match)
# ═══════════════════════════════════════════════════════════════════════════════
SKILL_CATEGORIES: dict[str, str] = {
    # LLM tooling
    "langchain": "llm_tooling",
    "llamaindex": "llm_tooling",
    "llama index": "llm_tooling",
    "dspy": "llm_tooling",
    "crewai": "llm_tooling",
    "autogen": "llm_tooling",
    "openai api": "llm_tooling",
    "openai": "llm_tooling",
    "chatgpt": "llm_tooling",
    "gpt-4": "llm_tooling",
    "gpt-3": "llm_tooling",
    "prompt engineering": "llm_tooling",
    "fine-tuning llm": "llm_tooling",
    "lora": "llm_tooling",
    "qlora": "llm_tooling",
    "peft": "llm_tooling",
    "rlhf": "llm_tooling",
    "hugging face": "llm_tooling",
    "huggingface": "llm_tooling",
    "transformers": "llm_tooling",
    # Vector / retrieval
    "pinecone": "vector_retrieval",
    "faiss": "vector_retrieval",
    "weaviate": "vector_retrieval",
    "qdrant": "vector_retrieval",
    "chromadb": "vector_retrieval",
    "chroma": "vector_retrieval",
    "milvus": "vector_retrieval",
    "rag": "vector_retrieval",
    "retrieval augmented": "vector_retrieval",
    "vector database": "vector_retrieval",
    "vector search": "vector_retrieval",
    "elasticsearch": "vector_retrieval",
    "opensearch": "vector_retrieval",
    "sentence-transformers": "vector_retrieval",
    "sentence transformers": "vector_retrieval",
    "embeddings": "vector_retrieval",
    # ML frameworks
    "pytorch": "ml_frameworks",
    "tensorflow": "ml_frameworks",
    "jax": "ml_frameworks",
    "keras": "ml_frameworks",
    "scikit-learn": "ml_frameworks",
    "sklearn": "ml_frameworks",
    "xgboost": "ml_frameworks",
    "lightgbm": "ml_frameworks",
    "catboost": "ml_frameworks",
    # MLOps
    "mlflow": "mlops_infra",
    "ray": "mlops_infra",
    "kubeflow": "mlops_infra",
    "airflow": "mlops_infra",
    "wandb": "mlops_infra",
    "weights & biases": "mlops_infra",
    "bentoml": "mlops_infra",
    "seldon": "mlops_infra",
    "triton": "mlops_infra",
    "docker": "mlops_infra",
    "kubernetes": "mlops_infra",
    # Data engineering
    "spark": "data_engineering",
    "pyspark": "data_engineering",
    "dbt": "data_engineering",
    "kafka": "data_engineering",
    "flink": "data_engineering",
    "airflow": "data_engineering",
    "snowflake": "data_engineering",
    "bigquery": "data_engineering",
    "redshift": "data_engineering",
    "apache beam": "data_engineering",
    # Cloud platforms
    "aws": "cloud_platforms",
    "sagemaker": "cloud_platforms",
    "gcp": "cloud_platforms",
    "vertex ai": "cloud_platforms",
    "azure": "cloud_platforms",
    "azure ml": "cloud_platforms",
    # Foundational ML
    "statistics": "foundational_ml",
    "statistical modeling": "foundational_ml",
    "linear algebra": "foundational_ml",
    "optimization": "foundational_ml",
    "probability": "foundational_ml",
    "bayesian": "foundational_ml",
    "deep learning": "foundational_ml",
    "machine learning": "foundational_ml",
    "neural networks": "foundational_ml",
    "nlp": "foundational_ml",
    "natural language processing": "foundational_ml",
    "computer vision": "foundational_ml",
    "image classification": "foundational_ml",
    "object detection": "foundational_ml",
    "reinforcement learning": "foundational_ml",
    "gans": "foundational_ml",
    "recommendation systems": "foundational_ml",
    # Programming languages
    "python": "programming_lang",
    "sql": "programming_lang",
    "scala": "programming_lang",
    "julia": "programming_lang",
    "java": "programming_lang",
    "c++": "programming_lang",
    "rust": "programming_lang",
    "go": "programming_lang",
    "r": "programming_lang",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Ecosystem launch dates — for temporal honeypot detection
# If a candidate claims skill usage from before the tool existed, it's a flag.
# ═══════════════════════════════════════════════════════════════════════════════
SKILL_LAUNCH_DATES: dict[str, str] = {
    "langchain": "2022-10",
    "llamaindex": "2022-11",
    "llama index": "2022-11",
    "pinecone": "2021-01",
    "weaviate": "2019-01",
    "dspy": "2023-01",
    "crewai": "2024-01",
    "faiss": "2017-03",
    "ray": "2018-09",
    "mlflow": "2018-06",
    "chromadb": "2022-10",
    "qdrant": "2021-05",
    "milvus": "2019-10",
    "lora": "2021-06",
    "qlora": "2023-05",
    "chatgpt": "2022-11",
    "gpt-4": "2023-03",
    "autogen": "2023-09",
    "bentoml": "2019-01",
}

# ═══════════════════════════════════════════════════════════════════════════════
# IT Services companies — entire career here = disqualifier penalty
# ═══════════════════════════════════════════════════════════════════════════════
SERVICE_COMPANIES: set[str] = {
    "tcs",
    "tata consultancy",
    "tata consultancy services",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "mindtree",
    "hcl",
    "hcl technologies",
    "tech mahindra",
    "cts",
    "l&t infotech",
    "lti",
    "ltimindtree",
    "mphasis",
    "hexaware",
    "persistent systems",
    "zensar",
    "cyient",
    "niit technologies",
    "birlasoft",
    "sonata software",
    "coforge",
    "happiest minds",
    "mastek",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Disqualifier penalties (subtracted from relevance score before behavioral mult)
# ═══════════════════════════════════════════════════════════════════════════════
PENALTIES = {
    "all_services": -0.35,       # Entire career at IT services
    "pure_research": -0.25,      # No production deployment evidence
    "job_hopper": -0.20,         # Avg tenure < 18 months across 4+ roles
    "wrong_domain": -0.20,       # CV/speech/robotics only, no NLP/IR
    "llm_wrapper_only": -0.15,   # Only recent LLM-wrapper work, no ML foundation
}

# ═══════════════════════════════════════════════════════════════════════════════
# JD-Adaptive Weight Engine — signal extraction keywords
# ═══════════════════════════════════════════════════════════════════════════════
SIGNAL_MAP: dict[str, list[str]] = {
    "urgency": [
        "day-1", "immediately", "production-ready", "no ramp", "ship from week 1",
        "hands-on", "own it from day one", "hit the ground running",
        "day 1", "day-1 ownership", "production deployment",
    ],
    "growth": [
        "fast learner", "grow with us", "early team", "we'll teach",
        "learning culture", "high growth", "evolving role",
        "potential over experience",
    ],
    "research": [
        "phd preferred", "publications", "novel", "state of the art",
        "research background", "advance the field", "first principles",
    ],
    "breadth": [
        "startup", "early stage", "generalist", "wear many hats", "zero-to-one",
        "founding team", "scrappy", "full-stack ml", "series a",
    ],
    "geo_strict": [
        "must be in", "india only", "bengaluru required", "on-site mandatory",
        "no remote", "in-office", "pune", "noida", "hybrid",
    ],
}

# Weight deltas per signal type — how each signal shifts dimension weights
SIGNAL_DELTAS: dict[str, dict[str, float]] = {
    "urgency": {
        "career_fit": +0.10,
        "skill_trust": +0.05,
        "career_velocity": -0.08,
        "semantic_fit": -0.07,
    },
    "growth": {
        "career_velocity": +0.12,
        "semantic_fit": +0.03,
        "career_fit": -0.08,
        "location_fit": -0.05,
        "skill_trust": -0.02,
    },
    "research": {
        "semantic_fit": +0.10,
        "career_velocity": +0.05,
        "career_fit": -0.08,
        "location_fit": -0.07,
    },
    "breadth": {
        "career_velocity": +0.08,
        "career_fit": -0.04,
        "skill_trust": -0.04,
    },
    "geo_strict": {
        "location_fit": +0.08,
    },
}

# Minimum weight floor — no dimension drops below this
WEIGHT_FLOOR = 0.05

# Noise threshold — ignore signals weaker than this
SIGNAL_NOISE_THRESHOLD = 0.15

# ═══════════════════════════════════════════════════════════════════════════════
# Title relevance keywords — for filtering AI/ML-relevant candidates
# ═══════════════════════════════════════════════════════════════════════════════

# Strongly relevant titles (high signal)
TITLE_KEYWORDS_STRONG: list[str] = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "data scientist", "deep learning", "nlp engineer",
    "research scientist", "research engineer",
    "applied scientist", "ai researcher",
    "machine learning", "artificial intelligence",
    "senior ai", "staff ai", "principal ai",
    "senior ml", "staff ml", "principal ml",
    "ai/ml", "ml/ai",
    "recommendation", "ranking engineer",
    "search engineer", "retrieval engineer",
    "computer vision engineer", "cv engineer",
]

# Moderately relevant titles (some signal)
TITLE_KEYWORDS_MODERATE: list[str] = [
    "data engineer", "analytics engineer",
    "software engineer", "backend engineer",
    "full stack", "fullstack",
    "platform engineer", "infrastructure engineer",
    "devops", "sre",
    "tech lead", "engineering manager",
    "data analyst", "business intelligence",
    "python developer", "developer",
]

# Irrelevant titles (strong negative signal — likely keyword stuffers)
TITLE_KEYWORDS_IRRELEVANT: list[str] = [
    "hr manager", "human resources",
    "accountant", "accounting",
    "marketing manager", "marketing",
    "sales executive", "sales manager", "sales",
    "content writer", "copywriter",
    "graphic designer", "ui designer",
    "mechanical engineer",
    "civil engineer",
    "electrical engineer",
    "chemical engineer",
    "operations manager",
    "project manager",
    "customer support", "customer service",
    "teacher", "professor",
    "lawyer", "legal",
    "finance manager", "financial analyst",
    "admin", "administrative",
    "receptionist",
    "nurse", "doctor",
]

# ═══════════════════════════════════════════════════════════════════════════════
# JD skills — skills the job description explicitly asks for
# Extracted manually from the JD analysis
# ═══════════════════════════════════════════════════════════════════════════════
JD_REQUIRED_SKILLS: list[str] = [
    # Must-haves from JD
    "embeddings", "sentence-transformers", "sentence transformers",
    "vector database", "pinecone", "weaviate", "qdrant", "milvus",
    "faiss", "elasticsearch", "opensearch",
    "python",
    "ndcg", "mrr", "map", "evaluation", "ranking",
    "retrieval", "search", "recommendation",
    # Nice-to-haves
    "lora", "qlora", "peft", "fine-tuning",
    "xgboost", "learning to rank",
    "distributed systems", "inference optimization",
]

JD_RELEVANT_SKILL_NAMES: set[str] = {
    # Broader set for skill trust scoring — lowercased
    "python", "sql", "pytorch", "tensorflow", "jax", "keras",
    "scikit-learn", "sklearn", "xgboost", "lightgbm",
    "numpy", "pandas", "scipy",
    "langchain", "llamaindex", "llama index",
    "pinecone", "weaviate", "qdrant", "faiss", "milvus", "chromadb",
    "rag", "retrieval", "embeddings", "vector search",
    "sentence-transformers", "sentence transformers",
    "huggingface", "hugging face", "transformers",
    "nlp", "natural language processing",
    "deep learning", "machine learning", "neural networks",
    "recommendation systems", "ranking", "search",
    "mlflow", "wandb", "weights & biases",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "spark", "airflow", "kafka",
    "lora", "qlora", "peft", "fine-tuning llms",
    "openai", "gpt", "prompt engineering",
    "statistics", "statistical modeling", "linear algebra",
    "a/b testing", "evaluation",
    "flask", "fastapi", "django",
    "git", "linux", "bash",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Location preferences — from the JD
# ═══════════════════════════════════════════════════════════════════════════════
PREFERRED_LOCATIONS: list[str] = [
    "pune", "noida",
]

TIER1_INDIAN_CITIES: list[str] = [
    "pune", "noida", "mumbai", "bangalore", "bengaluru",
    "hyderabad", "delhi", "gurgaon", "gurugram",
    "chennai", "kolkata", "new delhi", "navi mumbai",
    "ncr", "delhi ncr",
]

PREFERRED_COUNTRY = "india"

# ═══════════════════════════════════════════════════════════════════════════════
# Behavioral signal thresholds
# ═══════════════════════════════════════════════════════════════════════════════
BEHAVIORAL_CONFIG = {
    "inactivity_hard_penalty_days": 180,     # 6+ months inactive
    "inactivity_soft_penalty_days": 90,      # 3-6 months inactive
    "response_rate_low_threshold": 0.10,     # Very low response rate
    "response_rate_mid_threshold": 0.40,     # Below average response
    "response_time_slow_hours": 72,          # 3+ days to respond
    "notice_period_ideal_days": 30,          # JD prefers sub-30 day
    "notice_period_max_days": 90,            # Beyond this = harder bar
    "github_score_strong": 50,              # Strong GitHub activity
    "github_score_moderate": 20,            # Some GitHub activity
    "min_multiplier": 0.45,                 # Floor for behavioral multiplier
    "max_multiplier": 1.10,                 # Ceiling for behavioral multiplier
}

# ═══════════════════════════════════════════════════════════════════════════════
# Honeypot detection thresholds
# ═══════════════════════════════════════════════════════════════════════════════
HONEYPOT_CONFIG = {
    "expert_zero_duration_threshold": 2,      # Flag if ≥2 expert skills with 0 duration
    "career_duration_mismatch_ratio": 1.8,    # Flag if total career months > claimed * 1.8
    "max_expert_skills_per_year": 3,          # Flag if expert skills / years > this
    "temporal_grace_months": 6,               # Allow 6mo before launch date
    "honeypot_score_threshold": 0.6,          # Score above this = likely honeypot
}

# ═══════════════════════════════════════════════════════════════════════════════
# Experience range (from JD)
# ═══════════════════════════════════════════════════════════════════════════════
EXPERIENCE_RANGE = {
    "ideal_min": 5.0,
    "ideal_max": 9.0,
    "acceptable_min": 3.0,
    "acceptable_max": 15.0,
}

# ═══════════════════════════════════════════════════════════════════════════════
# BlindSpot feature
# ═══════════════════════════════════════════════════════════════════════════════
BLINDSPOT_BOOST_FACTOR = 0.08  # Positive blindspot delta multiplied by this

# ═══════════════════════════════════════════════════════════════════════════════
# Reference date for time-based calculations
# ═══════════════════════════════════════════════════════════════════════════════
REFERENCE_DATE = date(2026, 6, 15)  # Approximate "now" for the hackathon
