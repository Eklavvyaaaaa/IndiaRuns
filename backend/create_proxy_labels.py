import json

def get_relevance(title: str) -> int:
    title = title.lower()
    
    # Tier 3 (Highly Relevant)
    if any(t in title for t in ["ai engineer", "machine learning", "ml engineer", "search engineer", "recommendation", "ranking engineer", "applied scientist"]):
        return 3
        
    # Tier 2 (Relevant)
    if any(t in title for t in ["data engineer", "backend engineer", "software engineer", "platform engineer", "mlops"]):
        return 2
        
    # Tier 1 (Adjacent/Somewhat)
    if any(t in title for t in ["data analyst", "frontend engineer", "full stack", "cloud engineer", "devops"]):
        return 1
        
    # Tier 0 (Irrelevant)
    return 0

def main():
    ground_truth = {}
    print("Generating proxy ground truth from legacy_v1/candidates.jsonl...")
    
    with open("legacy_v1/candidates.jsonl", "r") as f:
        for line in f:
            cand = json.loads(line)
            cand_id = cand["candidate_id"]
            title = cand.get("profile", {}).get("current_title", "")
            
            relevance = get_relevance(title)
            ground_truth[cand_id] = relevance
            
    with open("backend/ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)
        
    print(f"Generated ground truth for {len(ground_truth)} candidates.")

if __name__ == "__main__":
    main()
