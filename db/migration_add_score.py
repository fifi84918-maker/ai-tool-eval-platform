"""Add score_total and grade columns to skills table.

Idempotent migration script (not using Alembic autogenerate).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text
from db import engine


def add_score_columns():
    """Add score_total and grade columns if they don't exist."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("skills")]
    
    added = []
    
    with engine.begin() as conn:
        # Add score_total column if not exists
        if "score_total" not in columns:
            conn.execute(text(
                "ALTER TABLE skills ADD COLUMN score_total REAL"
            ))
            added.append("score_total")
        
        # Add grade column if not exists
        if "grade" not in columns:
            conn.execute(text(
                "ALTER TABLE skills ADD COLUMN grade VARCHAR(2)"
            ))
            added.append("grade")
    
    if added:
        print(f"OK: added {', '.join(added)} columns")
    else:
        print("OK: columns already exist")


if __name__ == "__main__":
    add_score_columns()
