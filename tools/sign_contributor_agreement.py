"""tools/sign_contributor_agreement.py — first-time contributor signing flow.

Usage:
    python tools/sign_contributor_agreement.py
    python tools/sign_contributor_agreement.py --name "Jane Doe" --email jane@example.com --gh-handle janedoe
    python tools/sign_contributor_agreement.py --dry-run  # print only, don't write

Writes ``governance/contributors/<gh_handle>.json`` with sha256 of the agreement text,
the signer's metadata, and an ISO-8601 UTC timestamp. Idempotent: re-running with the
same handle is rejected unless --force is passed.

P6-T4 spec §16 — CONTRIBUTOR_AGREEMENT signing flow.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGREEMENT_PATH = REPO_ROOT / "docs" / "governance" / "contributor_agreement.md"
CONTRIBUTORS_DIR = REPO_ROOT / "governance" / "contributors"


def load_agreement(path: Path = AGREEMENT_PATH) -> tuple[str, str]:
    """Return (agreement_text, sha256_hex)."""
    text = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, digest


def make_signature(
    *,
    name: str,
    email: str,
    gh_handle: str,
    agreement_sha256: str,
    now: _dt.datetime | None = None,
) -> dict[str, str]:
    ts = (now or _dt.datetime.now(_dt.timezone.utc)).isoformat()
    return {
        "name": name,
        "email": email,
        "gh_handle": gh_handle,
        "agreement_sha256": agreement_sha256,
        "signed_at_utc": ts,
        "agreement_path": "docs/governance/contributor_agreement.md",
    }


def write_signature(sig: dict[str, str], *, force: bool = False) -> Path:
    CONTRIBUTORS_DIR.mkdir(parents=True, exist_ok=True)
    out = CONTRIBUTORS_DIR / f"{sig['gh_handle']}.json"
    if out.exists() and not force:
        raise FileExistsError(
            f"Signature already exists at {out}. Pass --force to overwrite."
        )
    out.write_text(json.dumps(sig, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sign the OPL-for-Cancer contributor agreement.")
    p.add_argument("--name", help="Your real name")
    p.add_argument("--email", help="Your email")
    p.add_argument("--gh-handle", help="Your GitHub handle (no @)")
    p.add_argument("--dry-run", action="store_true", help="Print only, do not write")
    p.add_argument("--force", action="store_true", help="Overwrite existing signature")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    text, digest = load_agreement()
    print("─" * 72)
    print(text)
    print("─" * 72)
    print(f"Agreement SHA-256: {digest}")
    print()

    name = args.name or (input("Your real name: ").strip() if sys.stdin.isatty() else "")
    email = args.email or (input("Your email: ").strip() if sys.stdin.isatty() else "")
    gh_handle = args.gh_handle or (
        input("Your GitHub handle (no @): ").strip() if sys.stdin.isatty() else ""
    )
    if not (name and email and gh_handle):
        print("ERROR: name + email + gh-handle all required.", file=sys.stderr)
        return 2

    sig = make_signature(
        name=name, email=email, gh_handle=gh_handle, agreement_sha256=digest
    )
    if args.dry_run:
        print("DRY-RUN — would write:")
        print(json.dumps(sig, indent=2, ensure_ascii=False))
        return 0
    out = write_signature(sig, force=args.force)
    print(f"Signed. Written to {out.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
