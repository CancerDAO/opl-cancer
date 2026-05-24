"""CLI entry point for opl-cancer skill (v1.2.0)."""
from datetime import datetime, timezone
from pathlib import Path

import click

from opl_cancer.experts.roster import ROSTER


@click.group(help="OPL for Cancer — your AI scientist team, only for you.")
@click.version_option()
def main() -> None:
    pass


@main.command(help="Show current OPL capability snapshot.")
def status() -> None:
    click.echo("OPL for Cancer — v1.2.0")
    click.echo(f"  Experts active: {len(ROSTER)} (Sid PI + Henry Auditor + 18 named experts)")
    click.echo("  Wave runners ready: Wave1 / Wave2 / Wave3 / Wave4")
    click.echo("  Integrators wired: 20+ (NCCN / PubMed / CT.gov / ChiCTR / FDA-EAP / NMPA-EAP / RxNorm / GEO / etc.)")
    click.echo("  License: Apache-2.0")
    click.echo("  Read DISCLAIMER.md before use — not clinical decision support; not for emergencies.")


@main.command(help="Initialize a new patient project directory.")
@click.argument("patient_code")
@click.option(
    "--root",
    type=click.Path(file_okay=False),
    default="patients",
    help="Root directory for patient projects (default: patients/).",
)
def init_patient(patient_code: str, root: str) -> None:
    base = Path(root) / patient_code
    for sub in ("memory", "pi_session", "inbox", "triggers", "archives"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    click.echo(f"Initialized patient project at: {base}")
    click.echo("Sid (PI) will activate when first trigger fires.")


@main.command(name="list-experts", help="List the 18-name expert roster.")
def list_experts() -> None:
    click.echo("OPL for Cancer — Expert Roster (18 experts active)")
    click.echo()
    click.echo("  sid       PI / Chief-of-Staff      (Sid Mukherjee homage)")
    click.echo("  henry     Auditor / IRB substitute (Henry Beecher homage)")
    click.echo("  " + "-" * 60)
    for name, profile in ROSTER.items():
        click.echo(f"  {name:<10}{profile.role:<28}{profile.inspiration}")


@main.command(
    name="acknowledge",
    help="Patient acknowledgment loop — confirm a pending L3/L4 risk-card. Spec §8 L4.",
)
@click.argument("card_id")
@click.option(
    "--outstanding-dir",
    type=click.Path(file_okay=False),
    default="outstanding",
    help="Directory of pending ack records (default: outstanding/).",
)
@click.option(
    "--serious-risks",
    type=click.Path(dir_okay=False),
    default="knowledge/serious_risks_per_drug.json",
    help="Path to the per-drug serious-risks catalogue.",
)
def acknowledge(card_id: str, outstanding_dir: str, serious_risks: str) -> None:
    """Mark a pending risk-card as patient-acknowledged.

    Spec §8 L4: writes patient_acknowledged_at ISO-timestamp.
    """
    from opl_cancer.validators.henry import HenryAuditor

    auditor = HenryAuditor(
        serious_risks_path=Path(serious_risks),
        outstanding_dir=Path(outstanding_dir),
    )
    ts = datetime.now(timezone.utc).isoformat()
    rec = auditor.acknowledge(card_id, acknowledged_at=ts)
    click.echo(f"Acknowledged card {card_id!r} at {ts}")
    click.echo(f"  level: {rec.get('level')}")
    click.echo(f"  risks: {len(rec.get('known_serious_risks', []))}")


@main.command(
    name="list-pending-acks",
    help="List risk-disclosure cards awaiting patient acknowledgment. Spec §8 L4.",
)
@click.option(
    "--outstanding-dir",
    type=click.Path(file_okay=False),
    default="outstanding",
    help="Directory of pending ack records (default: outstanding/).",
)
@click.option(
    "--serious-risks",
    type=click.Path(dir_okay=False),
    default="knowledge/serious_risks_per_drug.json",
    help="Path to the per-drug serious-risks catalogue.",
)
def list_pending_acks(outstanding_dir: str, serious_risks: str) -> None:
    from opl_cancer.validators.henry import HenryAuditor

    auditor = HenryAuditor(
        serious_risks_path=Path(serious_risks),
        outstanding_dir=Path(outstanding_dir),
    )
    pending = auditor.list_pending()
    if not pending:
        click.echo("No pending acks.")
        return
    for rec in pending:
        click.echo(
            f"  {rec['card_id']}  L{rec['level']}  {rec['claim_text'][:60]}"
        )


if __name__ == "__main__":
    main()
