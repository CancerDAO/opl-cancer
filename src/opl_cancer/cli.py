"""CLI entry point. P0 skeleton — only --help works."""
import click


@click.group(help="OPL for Cancer — your AI scientist team, only for you.")
@click.version_option()
def main() -> None:
    pass


@main.command(help="Show current OPL skeleton status.")
def status() -> None:
    click.echo("P0 Skeleton — no experts/tasks/integrators implemented yet.")


if __name__ == "__main__":
    main()
