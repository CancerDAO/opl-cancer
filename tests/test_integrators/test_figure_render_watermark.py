"""v2.3 P2-#18 — figure_render watermark tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.integrators.figure_render import (
    render_km_curve,
    watermark_directory,
    watermark_png,
)


def _seed_fig(figures_dir: Path, ident: str) -> Path:
    return Path(
        render_km_curve(
            out_path=figures_dir / f"fig_{ident}.png",
            arms=[{"label": "arm1", "durations": [1, 2, 3, 4], "events": [1, 1, 0, 1]}],
            title=f"test fig {ident}",
        )["path"]
    )


def test_watermark_png_produces_distinct_output(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    src = _seed_fig(figs, "1")
    out_path = figs / "fig_1_watermarked.png"
    record = watermark_png(
        in_path=src, out_path=out_path, banner_text="[REFERENCE CASE]"
    )
    assert Path(record["path"]).is_file()
    assert Path(record["path"]) == out_path
    assert record["size_bytes"] > 0
    # Source unchanged
    assert src.is_file()


def test_watermark_directory_iterates_and_is_idempotent(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _seed_fig(figs, "1")
    _seed_fig(figs, "2")
    recs = watermark_directory(figures_dir=figs, banner_text="[REFERENCE CASE]")
    assert len(recs) == 2
    # Run again — both watermarked outputs are skipped this time
    recs2 = watermark_directory(figures_dir=figs, banner_text="[REFERENCE CASE]")
    assert len(recs2) == 0


def test_watermark_directory_skips_non_fig_files(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _seed_fig(figs, "1")
    (figs / "fig_1.py").write_text("# reproducer\n", encoding="utf-8")
    (figs / "random.txt").write_text("not a fig", encoding="utf-8")
    recs = watermark_directory(figures_dir=figs, banner_text="[X]")
    assert len(recs) == 1


def test_watermark_directory_missing_dir_returns_empty(tmp_path: Path) -> None:
    recs = watermark_directory(figures_dir=tmp_path / "nope", banner_text="x")
    assert recs == []
