"""Static repository scanner for quality metrics.

This module provides real static analysis capabilities beyond simple heuristics.
Scans repository structure, code patterns, and security signals.
"""

import re
from pathlib import Path
from typing import Dict, List, Any


# Patterns for security scanning
SECRET_PATTERNS = [
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),  # OpenAI keys
    re.compile(r'ghp_[a-zA-Z0-9]{36,}'),  # GitHub PATs
    re.compile(r'xox[baprs]-[a-zA-Z0-9-]{10,}'),  # Slack tokens
    re.compile(r'"password"\s*[:=]\s*["\'][^"\']+'),  # Hardcoded passwords
]

# Directories to ignore during scan
IGNORE_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    'dist', 'build', '.next', 'out', 'target', '.pytest_cache'
}

# File extensions for text scanning
TEXT_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yml', '.yaml', '.md', '.txt'}


def scan_repository(repo_path: str) -> Dict[str, Any]:
    """Scan repository and return metrics, findings, and metadata.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with metrics, findings, and meta information
    """
    repo = Path(repo_path)
    findings: List[Dict[str, str]] = []
    
    # Initialize metadata
    meta = {
        "file_count": 0,
        "language": None,
        "has_readme": False,
        "has_tests": False,
        "has_ci": False,
        "has_dockerfile": False,
        "has_license": False,
        "has_security_md": False,
    }
    
    # Collect files (ignoring specified dirs)
    all_files: List[Path] = []
    language_counts: Dict[str, int] = {}
    
    for file_path in repo.rglob("*"):
        if file_path.is_file():
            # Skip if in ignored directory
            if any(ignore in file_path.parts for ignore in IGNORE_DIRS):
                continue
            
            all_files.append(file_path)
            meta["file_count"] += 1
            
            # Count language by extension
            ext = file_path.suffix
            if ext:
                language_counts[ext] = language_counts.get(ext, 0) + 1
    
    # Detect primary language
    if language_counts:
        primary_ext = max(language_counts, key=language_counts.get)
        lang_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.go': 'Go', '.rs': 'Rust', '.cpp': 'C++',
            '.c': 'C', '.rb': 'Ruby', '.php': 'PHP'
        }
        meta["language"] = lang_map.get(primary_ext, primary_ext[1:].upper())
    
    # Check for key files
    meta["has_readme"] = any((repo / name).exists() for name in ["README.md", "README.rst", "README.txt", "readme.md"])
    meta["has_tests"] = any(
        "test" in p.name.lower() or p.name.startswith("test_") 
        for p in all_files if p.suffix in {'.py', '.js', '.ts'}
    )
    meta["has_ci"] = (repo / ".github" / "workflows").exists()
    meta["has_dockerfile"] = (repo / "Dockerfile").exists()
    meta["has_license"] = any((repo / name).exists() for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "license"])
    meta["has_security_md"] = any((repo / name).exists() for name in ["SECURITY.md", ".github/SECURITY.md"])
    
    # Count test files
    test_files = [p for p in all_files if "test" in p.name.lower() and p.suffix in {'.py', '.js', '.ts'}]
    
    # Check for manifest/config files
    has_manifest = any((repo / name).exists() for name in [
        "package.json", "pyproject.toml", "pom.xml", "go.mod", "Cargo.toml", "SKILL.md", "manifest.json"
    ])
    has_lockfile = any((repo / name).exists() for name in [
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock", 
        "poetry.lock", "Pipfile.lock", "go.sum", "Cargo.lock"
    ])
    has_gitignore = (repo / ".gitignore").exists()
    has_makefile = any((repo / name).exists() for name in ["Makefile", "justfile"])
    has_examples = (repo / "examples").exists() or (repo / "docs").exists()
    has_docker_compose = any((repo / name).exists() for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"])
    
    # Lint/format config
    has_lint_config = any((repo / name).exists() for name in [
        ".eslintrc", ".eslintrc.json", ".prettierrc", "ruff.toml", ".ruff.toml"
    ]) or (repo / "pyproject.toml").exists()
    
    # Security scanning: check for .env files
    env_files = list(repo.glob(".env*"))
    if env_files:
        findings.append({
            "dimension": "security",
            "severity": "high",
            "message": f"Found {len(env_files)} .env file(s) that may contain secrets"
        })
    
    # Scan text files for secrets (limit to 200 files)
    secret_findings = 0
    todo_count = 0
    type_hint_files = []
    async_files = 0
    
    text_files = [f for f in all_files if f.suffix in TEXT_EXTENSIONS and f.stat().st_size < 1024 * 1024][:200]
    
    for file_path in text_files:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check for hardcoded secrets
            for pattern in SECRET_PATTERNS:
                if pattern.search(content):
                    secret_findings += 1
                    findings.append({
                        "dimension": "security",
                        "severity": "critical",
                        "message": f"Potential hardcoded secret in {file_path.name}"
                    })
                    break  # One finding per file
            
            # Count TODOs
            todo_count += len(re.findall(r'\b(TODO|FIXME|XXX)\b', content))
            
            # Check for type hints in Python files
            if file_path.suffix == '.py':
                has_hints = bool(re.search(r'(->|:\s*\w+\s*[,\)])', content))
                type_hint_files.append(has_hints)
            
            # Check for async patterns
            if file_path.suffix in {'.py', '.js', '.ts'}:
                if re.search(r'\b(async|await)\b', content):
                    async_files += 1
                    
        except Exception:
            continue
    
    if todo_count > 20:
        findings.append({
            "dimension": "security",
            "severity": "low",
            "message": f"High number of TODO/FIXME comments ({todo_count})"
        })
    
    # Calculate type hint ratio
    type_hint_ratio = sum(type_hint_files) / len(type_hint_files) if type_hint_files else 0
    
    # Count dependencies
    dep_count = 0
    for dep_file in ["requirements.txt", "package.json", "pyproject.toml"]:
        dep_path = repo / dep_file
        if dep_path.exists():
            try:
                content = dep_path.read_text(encoding='utf-8', errors='ignore')
                if dep_file == "requirements.txt":
                    dep_count = len([l for l in content.split('\n') if l.strip() and not l.startswith('#')])
                elif dep_file == "package.json":
                    import json
                    data = json.loads(content)
                    dep_count = len(data.get("dependencies", {})) + len(data.get("devDependencies", {}))
                elif dep_file == "pyproject.toml":
                    # Simple count of lines under [tool.poetry.dependencies] or [project.dependencies]
                    in_deps = False
                    for line in content.split('\n'):
                        if '[' in line and 'dependencies' in line.lower():
                            in_deps = True
                        elif in_deps and line.strip() and not line.startswith('['):
                            dep_count += 1
                        elif in_deps and line.startswith('['):
                            in_deps = False
            except Exception:
                pass
    
    # Calculate metrics
    metrics = {
        "accuracy": 0.0,
        "reliability": 0.0,
        "security": 100.0,  # Start at 100, deduct
        "performance": 20.0,  # Baseline
    }
    
    # Accuracy scoring
    if meta["has_readme"]:
        metrics["accuracy"] += 15
    if meta["has_tests"]:
        metrics["accuracy"] += 25
    if meta["has_ci"]:
        metrics["accuracy"] += 15
    if has_manifest:
        metrics["accuracy"] += 15
    if has_examples:
        metrics["accuracy"] += 10
    
    # Test coverage estimate
    if len(all_files) > 0:
        test_ratio = min(len(test_files) / len(all_files), 0.2)  # Cap at 20%
        metrics["accuracy"] += test_ratio * 100
    
    # Reliability scoring
    if has_manifest:
        metrics["reliability"] += 20
    if has_lockfile:
        metrics["reliability"] += 20
    if has_gitignore:
        metrics["reliability"] += 10
    if has_makefile:
        metrics["reliability"] += 10
    if type_hint_ratio > 0.3:
        metrics["reliability"] += 15
    if has_lint_config:
        metrics["reliability"] += 10
    metrics["reliability"] += 15  # Baseline
    
    # Security scoring (deduct from 100)
    if env_files:
        metrics["security"] -= 25
    metrics["security"] -= min(secret_findings * 15, 60)
    if todo_count > 20:
        metrics["security"] -= 5
    if meta["has_security_md"]:
        metrics["security"] += 20
    if has_lockfile:
        metrics["security"] += 10
    metrics["security"] = max(0, min(100, metrics["security"]))
    
    # Performance scoring
    if meta["has_dockerfile"]:
        metrics["performance"] += 20
    if has_docker_compose:
        metrics["performance"] += 10
    # Cache config check (simplified)
    if any((repo / name).exists() for name in ["next.config.js", "next.config.ts", "vite.config.js", "vite.config.ts"]):
        metrics["performance"] += 15
    
    # Dependency count scoring
    if dep_count < 20:
        metrics["performance"] += 20
    elif dep_count < 50:
        metrics["performance"] += 15
    elif dep_count < 100:
        metrics["performance"] += 10
    else:
        metrics["performance"] += 5
    
    if async_files > 0:
        metrics["performance"] += 10
    
    # Clamp all metrics to 0-100
    for key in metrics:
        metrics[key] = max(0, min(100, metrics[key]))
    
    return {
        "metrics": metrics,
        "findings": findings,
        "meta": meta,
    }
