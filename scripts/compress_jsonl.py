"""Compress large results/*/full*/games.jsonl files to games.jsonl.gz (the plain file is kept).

Every loader reads either form (`eval.tournament.games_file` / `read_records`), and the
plain files are git-ignored, so the ``.gz`` is what gets committed and shipped.

Usage:
    python scripts/compress_jsonl.py [--min-mb 20] [--root results]
"""
from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path


def compress(path: Path) -> Path:
    """Write ``path + '.gz'`` (deterministic: no timestamp or name in the header)."""
    out = path.with_name(path.name + ".gz")
    with path.open("rb") as src, out.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as dst:
            shutil.copyfileobj(src, dst)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-mb", type=float, default=20.0)
    ap.add_argument("--root", type=Path, default=Path("results"))
    args = ap.parse_args(argv)
    for p in sorted(args.root.glob("*/full*/games.jsonl")):
        if p.stat().st_size >= args.min_mb * 1e6:
            out = compress(p)
            print(f"{p}: {p.stat().st_size / 1e6:.1f} MB -> {out.name} {out.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
