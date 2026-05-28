"""v2.1 P0-#8: CT.gov site cross-verify via hospital-page lookup."""
from __future__ import annotations

from unittest.mock import patch

from opl_cancer.integrators.clinicaltrials import verify_site_open


def test_verify_site_open_uses_hospital_page():
    with patch(
        "opl_cancer.integrators.clinicaltrials._fetch_hospital_trial_page"
    ) as f:
        f.return_value = "Status: actively recruiting cohort A"
        result = verify_site_open("NCT01234567", "中山大学肿瘤防治中心")
        assert result["status"] == "verified_open"
        assert result["source"].startswith("http")


def test_verify_site_returns_unverified_on_404():
    with patch(
        "opl_cancer.integrators.clinicaltrials._fetch_hospital_trial_page"
    ) as f:
        f.return_value = None
        result = verify_site_open("NCT01234567", "中山大学肿瘤防治中心")
        assert result["status"] == "unverified"


def test_verify_site_unknown_hospital_in_map():
    result = verify_site_open("NCT01234567", "Some Unknown Hospital")
    assert result["status"] == "unverified"
    assert "hospital_not_in_map" in result.get("reason", "")


def test_verify_site_closed_marker():
    with patch(
        "opl_cancer.integrators.clinicaltrials._fetch_hospital_trial_page"
    ) as f:
        f.return_value = "本研究已结束 closed."
        result = verify_site_open("NCT01234567", "复旦大学附属肿瘤医院")
        assert result["status"] == "verified_closed"
