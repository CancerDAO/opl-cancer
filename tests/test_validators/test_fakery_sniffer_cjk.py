"""v2.6.0 — fakery sniffer must catch CJK (Chinese) placeholder language.

Audit finding (independent product review, 2026-05-29): the sniffer's pattern
set was English-only (``[speculative``, ``approximately \\d``, ``<insert PMID>``)
while OPL is a Chinese-primary product. The v2.5.1 B1 delivery scaffold ships a
patient brief full of Chinese placeholders ("这一节由 SKILL 主线程的 LLM 填充",
"(主线程 LLM 根据病情细节填充第 1 题)") that the sniffer was blind to — so the
ADR-0021 Invariant-3 anti-fakery guarantee had a hole for the product's primary
language. These are the failing-first tests.
"""
from __future__ import annotations

import pytest

from opl_cancer.validators.fakery_sniffer import scan_text

# The exact placeholder strings the v2.5.1 DeliveryRunner scaffold emits.
_CJK_PLACEHOLDERS = [
    "- 第 1 句 — 主治推荐:这一节由 SKILL 主线程的 LLM 填充。",
    "1. (主线程 LLM 根据病情细节填充第 1 题)",
    "- 主线程 LLM 从 Wave 1-4 的 claim 列表里挑出真实的行动项填充本节。",
    "这里是占位符,待补充。",
    "TODO: 待填写疗效数据",
]


@pytest.mark.parametrize("line", _CJK_PLACEHOLDERS)
def test_sniffer_catches_cjk_placeholder(line: str) -> None:
    findings = list(scan_text(line))
    assert findings, f"sniffer missed CJK placeholder: {line!r}"


def test_sniffer_still_clean_on_real_chinese_prose() -> None:
    """Must not over-fire on legitimate Chinese clinical prose."""
    real = (
        "根据 Awad 等人的研究 (PMID:34750504),客观缓解率为 23.2% (n=142)。\n"
        "您目前的方案是奥希替尼,CT 显示疾病进展。\n"
        "建议与主治医生讨论下一线治疗选择。"
    )
    assert list(scan_text(real)) == []


def test_sniffer_background_exemption_preserved_for_cjk() -> None:
    """[BACKGROUND] lines stay exempt even with the CJK patterns added."""
    bg = "[BACKGROUND] 这一节由 SKILL 主线程的 LLM 填充。"
    assert list(scan_text(bg)) == []
