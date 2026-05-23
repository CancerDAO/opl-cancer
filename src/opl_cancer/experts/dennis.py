"""Dennis — Cross-Border Coordinator expert. P4.5-T3.

Archetype: Dennis Lo 卢煜明 (cfDNA pioneer, US-CN-HK 跨界转化). Portfolio
focuses on US/JP/EU clinical-trial + EAP cross-border navigation, visa /
insurance / IRB jurisdiction chains. Founder-mode L4 boundary discipline —
never markets access; always frames the regulator + ethical + cost chain.
"""
from __future__ import annotations

from typing import ClassVar

from ._common import LLMBackedExpert


class DennisExpert(LLMBackedExpert):
    portfolio: ClassVar[tuple[str, ...]] = ("cross_border_navigation",)
    # F3 trials (CT.gov / ChiCTR / ISRCTN), F8 EAP registries.
    preferred_families: ClassVar[tuple[str, ...]] = ("F3", "F8")
