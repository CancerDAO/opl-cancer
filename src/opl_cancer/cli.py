"""CLI entry point for opl-cancer skill. P0 skeleton subcommands."""
from pathlib import Path

import click

from opl_cancer.experts.roster import ROSTER


@click.group(help="OPL for Cancer — your AI scientist team, only for you.")
@click.version_option()
def main() -> None:
    pass


@main.command(help="Show current OPL skeleton status.")
def status() -> None:
    click.echo("P0 Skeleton — no experts/tasks/integrators implemented yet.")
    click.echo(f"Experts registered (placeholders): {len(ROSTER)}")
    click.echo("See docs/superpowers/plans/ for active implementation plan.")


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
    click.echo("OPL for Cancer — Expert Roster (P0 placeholders)")
    click.echo()
    click.echo("  sid       PI / Chief-of-Staff      (Sid Mukherjee homage)")
    click.echo("  henry     Auditor / IRB substitute (Henry Beecher homage)")
    click.echo("  " + "-" * 60)
    for name, profile in ROSTER.items():
        click.echo(f"  {name:<10}{profile.role:<28}{profile.inspiration}")


if __name__ == "__main__":
    main()
