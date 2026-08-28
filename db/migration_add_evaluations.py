"""Migration: Create evaluations table for history tracking."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import engine, Base
from db.models import Evaluation

def migrate():
    """Create evaluations table."""
    print("Creating evaluations table...")
    Base.metadata.create_all(engine, tables=[Evaluation.__table__])
    print("OK: evaluations table created")

if __name__ == "__main__":
    migrate()
