import sys
sys.path.append(".")

import json
from app.ranking.consistency import ConsistencyLayer

layer = ConsistencyLayer()

test_cases = [
    {
        "name": "Synonym test — should be clean",
        "candidate": {
            "title": "VP of Engineering",
            "summary": "Technology executive with 12 years leading engineering teams and driving product strategy.",
            "skills": json.dumps([{"name": "System Design"}, {"name": "Team Leadership"}, {"name": "Python"}]),
            "career_history": json.dumps([
                {"title": "Head of Technology", "company": "FinTech Corp", "duration_months": 36, "description": "Led 40-person engineering org, defined technical roadmap"},
                {"title": "Senior Engineer", "company": "Wipro", "duration_months": 48, "description": "Built backend systems in Python"}
            ])
        },
        "expect": "clean — synonym VP vs Head of Technology should not be penalized"
    },
    {
        "name": "Inflation test — should be major_mismatch",
        "candidate": {
            "title": "Chief Technology Officer",
            "summary": "CTO with expertise in cloud and AI strategy.",
            "skills": json.dumps([{"name": "AWS"}, {"name": "Strategy"}, {"name": "Leadership"}]),
            "career_history": json.dumps([
                {"title": "Software Developer", "company": "Small Agency", "duration_months": 24, "description": "Built websites in React"},
                {"title": "Junior Developer", "company": "Freelance", "duration_months": 12, "description": "Wrote HTML and CSS"}
            ])
        },
        "expect": "major_mismatch — CTO title but only junior dev history"
    },
    {
        "name": "Clean strong candidate",
        "candidate": {
            "title": "Senior Data Scientist",
            "summary": "Data scientist with 6 years building ML models for fintech and ecommerce.",
            "skills": json.dumps([{"name": "Python"}, {"name": "Machine Learning"}, {"name": "SQL"}]),
            "career_history": json.dumps([
                {"title": "Data Scientist", "company": "Paytm", "duration_months": 36, "description": "Built recommendation models using Python and scikit-learn, improved conversion by 18%"},
                {"title": "Junior Data Analyst", "company": "Analytics Firm", "duration_months": 24, "description": "SQL analysis and reporting"}
            ])
        },
        "expect": "clean — strong match across all three dimensions"
    },
    {
        "name": "Thin data test — should be low confidence",
        "candidate": {
            "title": "Product Manager",
            "summary": "",
            "skills": json.dumps([]),
            "career_history": json.dumps([])
        },
        "expect": "low confidence — not enough data to judge"
    },
    {
        "name": "IT services candidate — should not be penalized",
        "candidate": {
            "title": "Senior Java Developer",
            "summary": "Backend developer specializing in Java microservices and cloud infrastructure.",
            "skills": json.dumps([{"name": "Java"}, {"name": "Spring Boot"}, {"name": "AWS"}]),
            "career_history": json.dumps([
                {"title": "Java Developer", "company": "TCS", "duration_months": 48, "description": "Built microservices in Java Spring Boot for banking clients, deployed on AWS"},
                {"title": "Junior Developer", "company": "Infosys", "duration_months": 24, "description": "Developed REST APIs in Java"}
            ])
        },
        "expect": "clean — IT services background but title and history fully align"
    }
]

print("Running ConsistencyLayer tests...\n")
for i, test in enumerate(test_cases):
    score = layer.score(test["candidate"])
    print(f"Test {i+1}: {test['name']}")
    print(f"  Score    : {score}")
    print(f"  Expected : {test['expect']}")
    print()