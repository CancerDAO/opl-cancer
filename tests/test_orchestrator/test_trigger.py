"""Test trigger event loop — spec §13."""
from pathlib import Path

from opl_cancer.orchestrator.trigger import (
    TriggerEvent,
    TriggerSource,
    scan_inbox,
)


def test_scan_empty_inbox_yields_no_events(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    events = list(scan_inbox(inbox))
    assert events == []


def test_scan_inbox_with_new_file_yields_filedrop_event(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "new_report.pdf").write_text("fake pdf bytes")
    events = list(scan_inbox(inbox))
    assert len(events) == 1
    assert events[0].source == TriggerSource.FILE_DROP
    assert events[0].data["filename"] == "new_report.pdf"


def test_trigger_event_record_has_timestamp(tmp_path: Path) -> None:
    e = TriggerEvent(
        source=TriggerSource.PATIENT_QUERY,
        data={"question": "what is my NGS?"},
    )
    assert e.timestamp != ""
