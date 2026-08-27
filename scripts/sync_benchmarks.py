"""Sync benchmarks from private repository.

This script pulls hidden test set from the private GitHub repository.
NEVER commit the actual benchmarks/ directory to the main repo.

Usage:
    export GITHUB_TOKEN_BENCHMARKS="ghp_..."
    python scripts/sync_benchmarks.py
"""

import hashlib
import json
import os
import sys
from pathlib import Path


def main():
    """Sync benchmarks from private repo and compute file hashes."""
    
    # Check for GitHub token
    token = os.environ.get("GITHUB_TOKEN_BENCHMARKS")
    if not token:
        print("ERROR: GITHUB_TOKEN_BENCHMARKS environment variable not set", file=sys.stderr)
        print("Please set it to your GitHub personal access token with repo scope.", file=sys.stderr)
        print("Example: export GITHUB_TOKEN_BENCHMARKS='ghp_...'", file=sys.stderr)
        sys.exit(1)
    
    # Security: Never log the token
    print("✓ GITHUB_TOKEN_BENCHMARKS is set")
    
    # Load manifest to get repo URL
    manifest_path = Path("benchmarks.manifest.json")
    if not manifest_path.exists():
        print("ERROR: benchmarks.manifest.json not found", file=sys.stderr)
        sys.exit(1)
    
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo_url = manifest["private_repo"]
    repo_ref = manifest.get("repo_ref", "main")
    
    print(f"Private repo: {repo_url}")
    print(f"Reference: {repo_ref}")
    
    # Check if benchmarks/ exists and is a git repo
    benchmarks_dir = Path("benchmarks")
    
    # NOTE: This is a skeleton script. Actual git operations are commented out
    # to prevent accidental execution during development/testing.
    # Uncomment the subprocess calls when ready to use in production.
    
    print("\n⚠️  SKELETON MODE: Git operations not executed")
    print("To enable actual sync, uncomment subprocess calls in this script\n")
    
    # Construct authenticated URL (token is injected, not stored)
    # SECURITY: Token is only in memory, never written to disk
    # authenticated_url = repo_url.replace("https://", f"https://{token}@")
    
    # if benchmarks_dir.exists() and (benchmarks_dir / ".git").exists():
    #     print("Pulling latest changes...")
    #     import subprocess
    #     result = subprocess.run(
    #         ["git", "-C", "benchmarks", "pull"],
    #         capture_output=True,
    #         text=True,
    #     )
    #     if result.returncode != 0:
    #         print(f"ERROR: git pull failed: {result.stderr}", file=sys.stderr)
    #         sys.exit(1)
    #     print("✓ Pull completed")
    # else:
    #     print("Cloning private repository...")
    #     import subprocess
    #     result = subprocess.run(
    #         ["git", "clone", authenticated_url, "benchmarks"],
    #         capture_output=True,
    #         text=True,
    #     )
    #     if result.returncode != 0:
    #         print(f"ERROR: git clone failed: {result.stderr}", file=sys.stderr)
    #         sys.exit(1)
    #     print("✓ Clone completed")
    
    print("Simulating sync completion...")
    
    # Compute hashes for all sample files
    print("\nComputing file hashes:")
    print("-" * 60)
    
    samples_dir = benchmarks_dir / "samples"
    if samples_dir.exists():
        for py_file in sorted(samples_dir.glob("*.py")):
            if py_file.name.startswith("__"):
                continue
            
            content = py_file.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Extract case_id from filename (convention: {case_id}.py)
            case_id = py_file.stem
            relative_path = py_file.relative_to(benchmarks_dir)
            
            print(f"case_id: {case_id}")
            print(f"  file: {relative_path}")
            print(f"  sha256: {file_hash}")
            print()
    else:
        print("(benchmarks/samples/ not found, skipping hash computation)")
    
    print("-" * 60)
    print("\n✓ Sync skeleton completed")
    print("\nNEXT STEPS:")
    print("1. Manually update benchmarks.manifest.json with the sha256 values above")
    print("2. Do NOT commit the benchmarks/ directory itself (it's gitignored)")
    print("3. Commit only the updated benchmarks.manifest.json if hashes changed")


if __name__ == "__main__":
    main()
