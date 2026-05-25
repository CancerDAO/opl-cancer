"""Compute runtime — bixbench Docker wrapper (v1.4) + native Python (v1.5)."""
from .native_runner import (
    NATIVE_IMAGE_TAG,
    NativeAnalysisRunner,
    NativeAnalysisRunnerError,
    select_compute_runner,
)
from .runner import BIXBENCH_IMAGE_TAG, BixbenchRunner, BixbenchRunResult

__all__ = [
    "BIXBENCH_IMAGE_TAG",
    "BixbenchRunResult",
    "BixbenchRunner",
    "NATIVE_IMAGE_TAG",
    "NativeAnalysisRunner",
    "NativeAnalysisRunnerError",
    "select_compute_runner",
]
