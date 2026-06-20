"""
data_loader.py — Load candidate data from JSONL or JSON files.

Provides both streaming (memory-efficient) and batch loading,
plus JD text loading utilities.
"""

import gzip
import json
from pathlib import Path
from typing import Generator


def load_candidates_stream(path: str) -> Generator[dict, None, None]:
    """
    Stream candidates one at a time from a JSONL or gzipped JSONL file.
    Memory efficient — only one candidate in memory at a time.
    
    Args:
        path: Path to .jsonl or .jsonl.gz file
        
    Yields:
        Individual candidate dicts
    """
    filepath = Path(path)
    
    if filepath.suffix == ".gz":
        opener = lambda: gzip.open(filepath, "rt", encoding="utf-8")
    elif filepath.suffix == ".jsonl":
        opener = lambda: open(filepath, "r", encoding="utf-8")
    elif filepath.suffix == ".json":
        # JSON array file — load and yield each element
        with open(filepath, "r", encoding="utf-8") as f:
            candidates = json.load(f)
        if isinstance(candidates, list):
            yield from candidates
        else:
            yield candidates
        return
    else:
        raise ValueError(f"Unsupported file format: {filepath.suffix}. Use .jsonl, .jsonl.gz, or .json")
    
    with opener() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSON at line {line_num}: {e}")


def load_candidates_batch(path: str, max_candidates: int | None = None) -> list[dict]:
    """
    Load all candidates into memory as a list.
    
    Args:
        path: Path to .jsonl, .jsonl.gz, or .json file
        max_candidates: Optional limit on number of candidates to load.
                        None = load all.
    
    Returns:
        List of candidate dicts
    """
    candidates = []
    for i, candidate in enumerate(load_candidates_stream(path)):
        if max_candidates is not None and i >= max_candidates:
            break
        candidates.append(candidate)
    
    print(f"  Loaded {len(candidates)} candidates from {Path(path).name}")
    return candidates


def load_sample_candidates(path: str, n: int = 50) -> list[dict]:
    """
    Load the first N candidates for quick testing.
    
    Args:
        path: Path to candidate file
        n: Number of candidates to load (default 50)
    
    Returns:
        List of first N candidate dicts
    """
    return load_candidates_batch(path, max_candidates=n)


def load_jd_text(path: str) -> str:
    """
    Load the job description text from a .txt or .md file.
    
    Args:
        path: Path to the JD text file
        
    Returns:
        JD text as a single string
    """
    filepath = Path(path)
    
    if not filepath.exists():
        raise FileNotFoundError(f"JD file not found: {path}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def get_candidate_ids(candidates: list[dict]) -> list[str]:
    """
    Extract ordered list of candidate IDs from a list of candidate dicts.
    
    Args:
        candidates: List of candidate dicts
        
    Returns:
        List of candidate_id strings in the same order
    """
    return [c["candidate_id"] for c in candidates]


def validate_candidate(candidate: dict) -> bool:
    """
    Quick sanity check that a candidate dict has required top-level fields.
    
    Args:
        candidate: A single candidate dict
        
    Returns:
        True if all required fields are present
    """
    required_fields = ["candidate_id", "profile", "career_history", "education", "skills", "redrob_signals"]
    return all(field in candidate for field in required_fields)


def count_candidates(path: str) -> int:
    """
    Count total candidates in a file without loading all into memory.
    
    Args:
        path: Path to candidate file
        
    Returns:
        Number of candidates
    """
    count = 0
    for _ in load_candidates_stream(path):
        count += 1
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.data_loader <path_to_candidates>")
        sys.exit(1)
    
    path = sys.argv[1]
    print(f"Loading candidates from: {path}")
    
    # Load first 5 for quick inspection
    candidates = load_sample_candidates(path, n=5)
    
    for c in candidates:
        valid = validate_candidate(c)
        cid = c.get("candidate_id", "UNKNOWN")
        title = c.get("profile", {}).get("current_title", "N/A")
        yoe = c.get("profile", {}).get("years_of_experience", "N/A")
        n_skills = len(c.get("skills", []))
        print(f"  {cid}: {title} | {yoe} yrs | {n_skills} skills | valid={valid}")
