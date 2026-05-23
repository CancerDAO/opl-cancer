"""Delivery layer — patient-facing artifacts (briefs, risk cards, ack loop). Spec §8."""
from opl_cancer.delivery.risk_card import (
    RiskDisclosureCard,
    RiskDisclosureCardError,
    render_risk_card_html,
    render_risk_card_markdown,
)

__all__ = [
    "RiskDisclosureCard",
    "RiskDisclosureCardError",
    "render_risk_card_html",
    "render_risk_card_markdown",
]
