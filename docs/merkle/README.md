# Merkle Integrity Verification

This directory contains the Merkle tree for verifying the integrity of the Maelstrom Runtime source files.

## Files

- `merkle.json` — Full Merkle tree with per-file SHA-256 hashes
- `merkle_root.txt` — Merkle root hash

## Recompute

```bash
python scripts/recompute_merkle.py
```

## Verify

Compare the root hash in `merkle_root.txt` against the recomputed value. Any file modification will produce a different root.
