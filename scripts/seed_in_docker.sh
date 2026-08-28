#!/bin/sh
# Seed database with sample data inside Docker container
cd /app && python scripts/seed_with_scores.py
