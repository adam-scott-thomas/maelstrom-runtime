#!/usr/bin/env python3
"""Recompute the Merkle tree for integrity verification.

Hashes all tracked source files and writes the tree to docs/merkle/.
"""
import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKED_EXTENSIONS = {".py", ".json", ".toml", ".md", ".tex"}
EXCLUDE_DIRS = {"_archive", "__pycache__", ".git", ".pytest_cache"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_files(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*")):
        if any(ex in p.parts for ex in EXCLUDE_DIRS):
            continue
        if p.is_file() and p.suffix in TRACKED_EXTENSIONS:
            files.append(p)
    return files


def build_merkle(files: list[Path], root: Path) -> dict:
    leaves = {}
    for f in files:
        rel = str(f.relative_to(root)).replace("\\", "/")
        leaves[rel] = file_hash(f)

    # Compute root hash from sorted leaf hashes
    combined = "".join(leaves[k] for k in sorted(leaves))
    merkle_root = hashlib.sha256(combined.encode()).hexdigest()

    return {
        "merkle_root": merkle_root,
        "files": leaves,
    }


def main():
    files = collect_files(PROJECT_ROOT)
    tree = build_merkle(files, PROJECT_ROOT)

    merkle_dir = PROJECT_ROOT / "docs" / "merkle"
    merkle_dir.mkdir(parents=True, exist_ok=True)

    (merkle_dir / "merkle.json").write_text(
        json.dumps(tree, indent=2), encoding="utf-8",
    )
    (merkle_dir / "merkle_root.txt").write_text(
        tree["merkle_root"], encoding="utf-8",
    )

    print(f"Merkle root: {tree['merkle_root']}")
    print(f"Files hashed: {len(tree['files'])}")
    print(f"Written to: {merkle_dir}")


if __name__ == "__main__":
    main()
