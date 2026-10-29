import gzip
from pathlib import Path

from core.rules import GameConfig
from eval.tournament import RegistryFactory, games_file, read_records, round_robin
from experiments.plots import latest_runs
from scripts import make_submission
from scripts.compress_jsonl import compress

SMALL = GameConfig(4, 3)


def _games(path: Path) -> list[str]:
    round_robin({"random": RegistryFactory("random"), "backtracking_d2": RegistryFactory("backtracking_d2")},
                SMALL, 0.02, 4, n_workers=1, seed=3, out_path=path)
    return [r.game_id for r in read_records(path)]


def test_records_read_the_same_from_plain_and_gzip_files(tmp_path: Path) -> None:
    plain = tmp_path / "games.jsonl"
    ids = _games(plain)
    assert len(ids) == 4
    gz = compress(plain)
    with gzip.open(gz, "rt", encoding="utf-8") as f:
        assert f.read() == plain.read_text(encoding="utf-8")  # lossless round trip
    expected = [r.to_json() for r in read_records(plain)]
    plain.unlink()
    assert games_file(tmp_path) == gz
    assert [r.to_json() for r in read_records(plain)] == expected  # plain name falls back to .gz
    assert [r.to_json() for r in read_records(gz)] == expected


def test_compression_is_deterministic_and_plain_file_wins_when_both_exist(tmp_path: Path) -> None:
    plain = tmp_path / "games.jsonl"
    _games(plain)
    first = compress(plain).read_bytes()
    assert compress(plain).read_bytes() == first
    assert games_file(tmp_path) == plain


def test_missing_games_file_reads_as_empty(tmp_path: Path) -> None:
    assert read_records(tmp_path / "games.jsonl") == []


def test_latest_runs_prefers_full_over_replicate_runs(tmp_path: Path) -> None:
    for name in ("20260101-000000", "full", "full_w6_0.1"):
        (tmp_path / "main_9x9" / name).mkdir(parents=True)
        (tmp_path / "main_9x9" / name / "summary.csv").write_text("x\n")
    assert latest_runs(tmp_path)["main_9x9"].name == "full"


def test_submission_ships_the_gz_and_not_the_plain_jsonl(tmp_path: Path) -> None:
    run = tmp_path / "results" / "main_9x9" / "full"
    run.mkdir(parents=True)
    (run / "games.jsonl").write_text("{}\n")
    (run / "games.jsonl.gz").write_bytes(b"gz")
    (run / "summary.csv").write_text("x\n")
    small = tmp_path / "results" / "scaling" / "full"
    small.mkdir(parents=True)
    (small / "games.jsonl").write_text("{}\n")
    files = {p.as_posix() for p in make_submission.collect(tmp_path)}
    assert "results/main_9x9/full/games.jsonl.gz" in files
    assert "results/main_9x9/full/games.jsonl" not in files
    assert "results/scaling/full/games.jsonl" in files
