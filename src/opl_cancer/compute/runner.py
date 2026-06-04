"""BixbenchRunner — Docker subprocess wrapper for Aviv's data-analysis notebooks.

P3-T10. Lifted from robin/finch/src/fhda/data_analysis_env.py interface; trimmed
to a single ``run_notebook`` entrypoint that maps:

    docker run --rm \\
      -v <workdir>:/workspace \\
      <BIXBENCH_IMAGE_TAG> \\
      jupyter execute /workspace/<notebook>

**Env gate**: actual docker invocation only runs when ``OPL_BIXBENCH_LIVE=1``.
Without the flag, ``run_notebook`` returns a dry-run dict describing what would
be executed (used for CI + Wave 3 E2E tests).

This matches no-silent-fallback policy — live mode raises on docker
errors (no silent degradation). Dry-run is explicit metadata only, never
masquerading as a real run.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


BIXBENCH_IMAGE_TAG = "opl-cancer/bixbench:v0.3.0-p3"
DOCKERFILE_NAME = "bixbench.Dockerfile"
_LIVE_ENV = "OPL_BIXBENCH_LIVE"


@dataclass
class BixbenchRunResult:
    mode: str  # "dry-run" | "live"
    image: str
    notebook_path: str
    workdir: str
    timeout_s: int
    docker_cmd: list[str]
    returncode: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BixbenchRunnerError(RuntimeError):
    """Raised when live docker invocation fails (no-silent-fallback policy)."""


class BixbenchRunner:
    """Run a Jupyter notebook inside the bixbench image.

    Defaults to dry-run unless ``OPL_BIXBENCH_LIVE=1`` is set.
    """

    def __init__(
        self,
        image: str = BIXBENCH_IMAGE_TAG,
        *,
        docker_binary: str = "docker",
        live_env_name: str = _LIVE_ENV,
    ) -> None:
        self.image = image
        self.docker_binary = docker_binary
        self.live_env_name = live_env_name

    def is_live(self) -> bool:
        return os.environ.get(self.live_env_name, "") == "1"

    def build_command(
        self, *, notebook_path: Path, workdir: Path, timeout_s: int
    ) -> list[str]:
        return [
            self.docker_binary,
            "run",
            "--rm",
            "-v",
            f"{workdir.resolve()}:/workspace",
            "-w",
            "/workspace",
            self.image,
            "timeout",
            str(timeout_s),
            "jupyter",
            "execute",
            f"/workspace/{notebook_path.name}",
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
                mode="dry-run",
                image=self.image,
                notebook_path=str(notebook_path),
                workdir=str(workdir),
                timeout_s=timeout_s,
                docker_cmd=cmd,
                extra={"reason": f"{self.live_env_name} != 1; skipped real docker run"},
            )

        if shutil.which(self.docker_binary) is None:
            raise BixbenchRunnerError(
                f"docker binary {self.docker_binary!r} not on PATH in live mode"
            )
        if not notebook_path.exists():
            raise BixbenchRunnerError(f"notebook not found: {notebook_path}")

        try:
            proc = subprocess.run(  # noqa: S603 — controlled args
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s + 60,  # outer guard
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise BixbenchRunnerError(
                f"bixbench timeout after {timeout_s}s: {e}"
            ) from e
        except FileNotFoundError as e:
            raise BixbenchRunnerError(f"docker binary not found: {e}") from e

        if proc.returncode != 0:
            raise BixbenchRunnerError(
                f"bixbench exit {proc.returncode}: stderr={proc.stderr[-500:]!r}"
            )

        return BixbenchRunResult(
            mode="live",
            image=self.image,
            notebook_path=str(notebook_path),
            workdir=str(workdir),
            timeout_s=timeout_s,
            docker_cmd=cmd,
            returncode=proc.returncode,
            stdout_tail=proc.stdout[-500:],
            stderr_tail=proc.stderr[-500:],
        )
