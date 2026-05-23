"""Test append-only JSONL provenance journal."""
from pathlib import Path

from opl_cancer.provenance.journal import ProvenanceJournal


def test_append_writes_one_jsonl_line_per_record(tmp_path: Path) -> None:
    j = ProvenanceJournal(path=tmp_path / "provenance.jsonl")
    j.append({"claim_hash": "sha256:" + "0" * 64, "claim": "x"})
    j.append({"claim_hash": "sha256:" + "1" * 64, "claim": "y"})
    lines = (tmp_path / "provenance.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2


def test_journal_is_append_only_never_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "p.jsonl"
    path.write_text('{"existing": "record"}\n')
    j = ProvenanceJournal(path=path)
    j.append({"new": "record"})
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert '"existing"' in lines[0]
    assert '"new"' in lines[1]


def test_iter_yields_records(tmp_path: Path) -> None:
    j = ProvenanceJournal(path=tmp_path / "p.jsonl")
    j.append({"a": 1})
    j.append({"b": 2})
    records = list(j.iter_records())
    assert records == [{"a": 1}, {"b": 2}]
