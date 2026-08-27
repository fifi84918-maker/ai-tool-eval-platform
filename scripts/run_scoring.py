"""Command-line script to score sample skills.

Demonstrates scoring engine usage with hardcoded sample data.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring import score_skill


# Sample skill metrics (hardcoded for demonstration)
SAMPLE_SKILLS = [
    {
        "name": "doc-skill (S1-green)",
        "metrics": {
            "accuracy": 92.0,
            "reliability": 88.0,
            "security": 85.0,
            "performance": 90.0,
        },
    },
    {
        "name": "loose-repo (S2-no-skillmd)",
        "metrics": {
            "accuracy": 78.0,
            "reliability": 72.0,
            "security": 65.0,
            "performance": 80.0,
        },
    },
    {
        "name": "cleaner-skill (S3-highrisk-perms)",
        "metrics": {
            "accuracy": 85.0,
            "reliability": 80.0,
            "security": 55.0,  # Lower due to high-risk permissions
            "performance": 82.0,
        },
    },
    {
        "name": "apikey-leak (S4-secrets)",
        "metrics": {
            "accuracy": 70.0,
            "reliability": 65.0,
            "security": 20.0,  # Very low due to secrets leak
            "performance": 75.0,
        },
    },
    {
        "name": "sandbox-blocked (S5-die-early)",
        "metrics": {
            "accuracy": 45.0,
            "reliability": 40.0,
            "security": 50.0,
            "performance": 35.0,
        },
    },
]


def main():
    """Score all sample skills and print results."""
    print("=" * 60)
    print("Skill Scoring Results")
    print("=" * 60)
    print()
    
    for skill in SAMPLE_SKILLS:
        result = score_skill(skill["metrics"])
        
        print(f"Skill: {skill['name']}")
        print(f"  Total Score: {result['total']:.2f}")
        print(f"  Grade: {result['grade']}")
        print(f"  Breakdown:")
        for dim, contrib in result["breakdown"].items():
            print(f"    {dim}: {contrib:.2f}")
        print()
    
    print("=" * 60)
    print("Grade Scale:")
    print("  A: >= 90 (Excellent)")
    print("  B: >= 75 (Good)")
    print("  C: >= 60 (Acceptable)")
    print("  D: >= 40 (Poor)")
    print("  U: <  40 (Unacceptable)")
    print("=" * 60)


if __name__ == "__main__":
    main()
