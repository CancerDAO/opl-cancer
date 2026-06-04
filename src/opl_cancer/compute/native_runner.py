"""NativeAnalysisRunner — Docker-free Wave-3 compute path. v1.5 P0-1.

Drop-in alternative to ``BixbenchRunner`` when Docker is unavailable or the
patient run prefers a native-Mac / native-Linux Python invocation. Same public
contract (``run_notebook(notebook_path=, workdir=, timeout_s=)`` returning a
``BixbenchRunResult``-shape dataclass), so ``Wave3Runner`` can swap them
freely.

Execution modes:
  * ``"native-live"``  — when ``OPL_NATIVE_LIVE=1`` AND ``jupyter`` is on PATH,
    we shell out to ``jupyter nbconvert --execute --to notebook --inplace``
    in the local Python env. No container, no isolation. Same network access
    as the calling process.
  * ``"native-dry-run"`` — when ``OPL_NATIVE_LIVE != 1`` OR ``jupyter`` is not
    available. Returns metadata only (matches Bixbench dry-run semantics).

Per no-silent-fallback policy — live mode raises on errors (no silent
degradation). Per docs/ANTI_PATTERNS_v1.4.md AP-1 — Wave 3 is critical-path
and must not silently skip. The orchestration layer chooses between
``NativeAnalysisRunner`` and ``BixbenchRunner`` once at construction; if both
are unavailable it should preflight-abort (not skip).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .runner import BixbenchRunResult

_NATIVE_LIVE_ENV = "OPL_NATIVE_LIVE"
NATIVE_IMAGE_TAG = "opl-cancer/native:v1.5"


class NativeAnalysisRunnerError(RuntimeError):
    """Raised when live native invocation fails (no-silent-fallback policy)."""


class NativeAnalysisRunner:
    """Run a Jupyter notebook in the local Python environment, no Docker.

    Defaults to dry-run unless ``OPL_NATIVE_LIVE=1`` is set.
    """

    def __init__(
        self,
        *,
        jupyter_binary: str = "jupyter",
        live_env_name: str = _NATIVE_LIVE_ENV,
        image: str = NATIVE_IMAGE_TAG,
    ) -> None:
        self.jupyter_binary = jupyter_binary
        self.live_env_name = live_env_name
        self.image = image

    def is_live(self) -> bool:
        return os.environ.get(self.live_env_name, "") == "1"

    def is_available(self) -> bool:
        """Returns True if jupyter binary is on PATH; used by preflight."""
        return shutil.which(self.jupyter_binary) is not None

    def build_command(
        self, *, notebook_path: Path, workdir: Path, timeout_s: int
    ) -> list[str]:
        # `--execute --inplace` runs in-place; `--ExecutePreprocessor.timeout`
        # provides cell-level timeout. We still wrap with outer subprocess
        # timeout for safety.
        return [
            self.jupyter_binary,
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--inplace",
            f"--ExecutePreprocessor.timeout={timeout_s}",
            f"--ExecutePreprocessor.cwd={workdir.resolve()}",
            str(notebook_path),
        ]

    def run_notebook(
        self,
        *,
        notebook_path: Path,
        workdir: Path,
        timeout_s: int = 1800,
    ) -> BixbenchRunResult:
        notebook_path = Path(notebook_path)
        workdir = Path(workdir)
        cmd = self.build_command(
            notebook_path=notebook_path, workdir=workdir, timeout_s=timeout_s
        )

        if not self.is_live():
            return BixbenchRunResult(
                mode="native-dry-run",
                image=self.image,
                notebook_path=str(notebook_path),
                workdir=str(workdir),
                timeout_s=timeout_s,
                docker_cmd=cmd,  # field-name retained for cross-runner compat
                extra={
                    "reason": (
                        f"{self.live_env_name} != 1; skipped real jupyter run"
                    ),
                    "runner": "native",
                },
            )

        if not self.is_available():
            raise NativeAnalysisRunnerError(
                f"jupyter binary {self.jupyter_binary!r} not on PATH in live mode"
            )
        if not notebook_path.exists():
            raise NativeAnalysisRunnerError(f"notebook not found: {notebook_path}")

        try:
            proc = subprocess.run(  # noqa: S603 — controlled args
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s + 60,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise NativeAnalysisRunnerError(
                f"native jupyter timeout after {timeout_s}s: {e}"
            ) from e
        except FileNotFoundError as e:
            raise NativeAnalysisRunnerError(f"jupyter binary not found: {e}") from e

        if proc.returncode != 0:
            raise NativeAnalysisRunnerError(
                f"native jupyter exit {proc.returncode}: stderr={proc.stderr[-500:]!r}"
            )

        return BixbenchRunResult(
            mode="native-live",
            image=self.image,
            notebook_path=str(notebook_path),
            workdir=str(workdir),
            timeout_s=timeout_s,
            docker_cmd=cmd,
            returncode=proc.returncode,
            stdout_tail=proc.stdout[-500:],
            stderr_tail=proc.stderr[-500:],
            extra={"runner": "native"},
        )


def select_compute_runner(
    *,
    prefer: str = "auto",
    bixbench: Any = None,
    native: Any = None,
) -> Any:
    """Compute-runner selector used by Wave 3 orchestration.

    ``prefer`` ∈ {"auto", "native", "bixbench"}. In ``auto`` we prefer
    ``native`` (no Docker required, faster startup, same Python env as the
    caller). ``bixbench`` is the historical default — kept for users with
    heavy R / bioconductor dependencies.

    If a preferred runner is unavailable, falls through to the other. If
    neither is available, raises — Wave 3 must not silently skip
    (AP-1 / AP-14).
    """
    if bixbench is None:
        from .runner import BixbenchRunner

        bixbench = BixbenchRunner()
    if native is None:
        native = NativeAnalysisRunner()

    if prefer == "bixbench":
        # explicit user request; let it fail loud if Docker missing
        return bixbench
    if prefer == "native":
        if not native.is_available():
            raise RuntimeError(
                "NativeAnalysisRunner requested but jupyter not on PATH. "
                "Install jupyter (e.g. `pip install jupyter`) or set "
                "prefer='bixbench' if you have Docker + the bixbench image."
            )
        return native

    # auto — prefer native, fall back to bixbench
    if native.is_available():
        return native
    if shutil.which(bixbench.docker_binary) is not None:
        return bixbench
    raise RuntimeError(
        "Neither jupyter (native) nor docker (bixbench) is on PATH. "
        "Wave 3 cannot proceed. Install one of them or change preflight."
    )
