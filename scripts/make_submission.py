"""Build HW2_<NAME>.zip and check that it works from a clean environment.

The archive holds the source, tests, docs, configs, README, requirements and the
FULL results only: quick-run directories (``results/<config>/<YYYYMMDD-HHMMSS>``),
caches and ``.git`` are left out. Unless ``--no-verify`` is given, the archive is
unpacked into a temporary directory, a fresh virtual environment is created,
``requirements.txt`` is installed and ``pytest -q -m "not slow"`` is run there.

Usage:
    python scripts/make_submission.py --name TEAM [--out DIR] [--no-verify]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_DIRS = ("core", "agents", "eval", "gui", "experiments", "scripts", "tests", "docs")
TOP_FILES = ("README.md", "requirements.txt", "pyproject.toml")
QUICK_RUN = re.compile(r"^\d{8}-\d{6}$")
SKIP_PARTS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", "venv", ".venv"}


def _skip(path: Path) -> bool:
    return bool(SKIP_PARTS & set(path.parts)) or path.suffix == ".pyc"


def collect(root: Path) -> list[Path]:
    """Files to ship, relative to ``root``, sorted."""
    out: set[Path] = set()
    for d in CODE_DIRS:
        out.update(p.relative_to(root) for p in (root / d).rglob("*") if p.is_file())
    out.update(Path(f) for f in TOP_FILES if (root / f).is_file())
    for p in (root / "results").rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(QUICK_RUN.match(part) for part in rel.parts):
            continue
        out.add(rel)
    return sorted(q for q in out if not _skip(q))


def build_zip(root: Path, out_path: Path) -> list[Path]:
    """Write the archive (all entries under one top-level folder) and return the file list."""
    files = collect(root)
    folder = out_path.stem
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(root / rel, f"{folder}/{rel.as_posix()}")
    return files


def verify(zip_path: Path) -> int:
    """Unpack, create a venv, install requirements and run the fast tests; return the exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp_dir / "unpacked")
        project = tmp_dir / "unpacked" / zip_path.stem
        venv = tmp_dir / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = venv / ("Scripts" if sys.platform == "win32" else "bin") / "python"
        steps = [
            [str(py), "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            [str(py), "-m", "pytest", "-q", "-m", "not slow", "-p", "no:cacheprovider"],
        ]
        for cmd in steps:
            print("+", " ".join(cmd), flush=True)
            code = subprocess.run(cmd, cwd=project).returncode
            if code != 0:
                return code
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True, help="group name used in HW2_<NAME>.zip")
    ap.add_argument("--out", type=Path, default=ROOT, help="directory for the zip")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args(argv)
    out_path = args.out / f"HW2_{args.name}.zip"
    files = build_zip(ROOT, out_path)
    size_mb = out_path.stat().st_size / 1e6
    print(f"{out_path}: {len(files)} files, {size_mb:.1f} MB")
    if args.no_verify:
        return 0
    code = verify(out_path)
    print("verification:", "OK" if code == 0 else f"FAILED (exit {code})")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
