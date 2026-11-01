"""Build HW2_<NAME>.zip and check that it works from a clean environment.

The archive holds the source, tests, docs, configs, README, requirements and the
FULL results only (large ``games.jsonl`` files as ``.jsonl.gz``; the plain file is left out
whenever a ``.gz`` sibling exists): quick-run directories (``results/<config>/<YYYYMMDD-HHMMSS>``),
caches and ``.git`` are left out. Unless ``--no-verify`` is given, the archive is
unpacked into a temporary directory, a fresh virtual environment is created,
``requirements.txt`` is installed and ``pytest -q -m "not slow"`` is run there.

``--lite`` builds a small archive (target < 20 MB): every ``games.jsonl[.gz]`` larger than 2 MB is
left out (summary.csv, puzzles, tables, figures and failure_cases.md stay) and ``results/OMITTED_DATA.md``
lists what was left out, with sizes and sha256. The default (full) archive is unchanged.

Usage:
    python scripts/make_submission.py --name TEAM [--out DIR] [--no-verify] [--lite]
"""
from __future__ import annotations

import argparse
import hashlib
import os
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
LARGE_BYTES = 20_000_000
LITE_BYTES = 2_000_000
OMITTED_NOTE = "results/OMITTED_DATA.md"
SKIP_PARTS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", "venv", ".venv"}


def _skip(path: Path) -> bool:
    return bool(SKIP_PARTS & set(path.parts)) or path.suffix == ".pyc"


def _is_games_file(path: Path) -> bool:
    return path.name in ("games.jsonl", "games.jsonl.gz")


def collect(root: Path, lite: bool = False) -> list[Path]:
    """Files to ship, relative to ``root``, sorted.

    With ``lite`` every games file larger than `LITE_BYTES` is left out (see `omitted`).
    """
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
        if lite and _is_games_file(p) and p.stat().st_size > LITE_BYTES:
            continue
        if p.suffix == ".jsonl" and p.with_name(p.name + ".gz").exists():
            continue
        if p.suffix == ".jsonl" and p.stat().st_size > LARGE_BYTES and not lite:
            print(f"warning: {rel} is {p.stat().st_size / 1e6:.0f} MB and has no .gz "
                  "(python scripts/compress_jsonl.py)")
        out.add(rel)
    return sorted(q for q in out if not _skip(q))


def omitted(root: Path) -> list[Path]:
    """Full-run games files (``.jsonl.gz`` preferred over a plain twin) that ``--lite`` leaves out."""
    kept = set(collect(root, lite=True))
    return [r for r in collect(root) if _is_games_file(r) and r not in kept]


def omitted_note(root: Path, names: list[Path]) -> str:
    """Markdown listing of the left-out files (size, sha256) and how to restore them."""
    lines = [
        "# Data left out of this lite archive", "",
        "The full game records are not in this archive. Download them from [TODO: link Drive/GitHub Release]",
        "and unpack each file to the same path (keep the `.gz`; every loader reads it directly). Then",
        "`python -m experiments.plots && python -m experiments.tables && python -m experiments.failure_cases && python -m experiments.nps_hist && python -m experiments.plot_growth`",
        "regenerate every figure and table; `summary.csv` can be",
        "rebuilt with `experiments.run.write_summary` (see README, section Reproducibility).", "",
        "| file | size (bytes) | sha256 |", "|---|---|---|"]
    for r in names:
        data = (root / r).read_bytes()
        lines.append(f"| `{r.as_posix()}` | {len(data)} | `{hashlib.sha256(data).hexdigest()}` |")
    return "\n".join(lines) + "\n"


def build_zip(root: Path, out_path: Path, lite: bool = False) -> list[Path]:
    """Write the archive (all entries under one top-level folder) and return the file list."""
    files = collect(root, lite)
    folder = out_path.stem
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(root / rel, f"{folder}/{rel.as_posix()}")
        if lite:
            z.writestr(f"{folder}/{OMITTED_NOTE}", omitted_note(root, omitted(root)))
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
            [str(py), "-m", "gui.app", "--headless-check"],
            [str(py), "-m", "pytest", "-q", "-m", "not slow", "-p", "no:cacheprovider"],
        ]
        env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "PYGAME_HIDE_SUPPORT_PROMPT": "1"}
        for cmd in steps:
            print("+", " ".join(cmd), flush=True)
            code = subprocess.run(cmd, cwd=project, env=env).returncode
            if code != 0:
                return code
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True, help="group name used in HW2_<NAME>.zip")
    ap.add_argument("--out", type=Path, default=ROOT, help="directory for the zip")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--lite", action="store_true",
                    help="leave out games files > 2 MB (small archive, no raw game records)")
    args = ap.parse_args(argv)
    out_path = args.out / f"HW2_{args.name}{'_lite' if args.lite else ''}.zip"
    files = build_zip(ROOT, out_path, args.lite)
    size_mb = out_path.stat().st_size / 1e6
    raw_mb = sum((ROOT / f).stat().st_size for f in files) / 1e6
    print(f"{out_path}: {len(files)} files, zip {size_mb:.1f} MB (uncompressed content {raw_mb:.1f} MB)")
    if args.no_verify:
        return 0
    code = verify(out_path)
    print("verification:", "OK" if code == 0 else f"FAILED (exit {code})")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
