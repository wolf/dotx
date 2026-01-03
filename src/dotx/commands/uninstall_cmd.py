"""Uninstall command for dotx CLI."""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from dotx.database import InstallationDB
from dotx.options import is_verbose_mode
from dotx.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan
from dotx.uninstall import plan_uninstall


def register_command(app: typer.Typer):
    """Register the uninstall command with the Typer app."""

    @app.command()
    def uninstall(
        ctx: typer.Context,
        sources: Annotated[
            list[Path],
            typer.Argument(
                help="Source package directories to uninstall",
                exists=True,
                file_okay=False,
                dir_okay=True,
                readable=True,
            ),
        ],
    ):
        """Uninstall source packages from target directory."""
        logger.info("uninstall starting")
        console = Console()
        verbose = is_verbose_mode(ctx)

        # Get target from options
        target_path = Path(ctx.obj.get("TARGET", Path.home())) if ctx.obj else Path.home()

        if sources:
            plans: list[tuple[Path, Plan]] = []
            for source_package in sources:
                plan: Plan = plan_uninstall(source_package, target_path)
                log_extracted_plan(
                    plan,
                    description=f"Actual plan to uninstall {source_package}",
                    actions_to_extract={Action.UNLINK},
                )
                plans.append((source_package, plan))

            # Count total actions
            total_actions = sum(
                len(extract_plan(plan, {Action.UNLINK}))
                for _, plan in plans
            )

            # Open database and execute all plans with progress
            with InstallationDB() as db:
                if verbose:
                    # Verbose: show each file
                    for source_package, plan in plans:
                        console.print(f"[cyan]Uninstalling {source_package.name}...[/cyan]")
                        for node in extract_plan(plan, {Action.UNLINK}):
                            console.print(f"  {node.relative_destination_path}")
                        execute_plan(source_package, target_path, plan, db)
                else:
                    # Default: show progress bar
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        console=console,
                    ) as progress:
                        task = progress.add_task("Uninstalling...", total=total_actions)
                        for source_package, plan in plans:
                            progress.update(task, description=f"Uninstalling {source_package.name}...")
                            execute_plan(source_package, target_path, plan, db)
                            progress.advance(task, len(extract_plan(plan, {Action.UNLINK})))

            # Show summary
            total_removed = sum(
                len(extract_plan(plan, {Action.UNLINK}))
                for _, plan in plans
            )
            console.print(f"\n[green]✓ Removed {total_removed} symlink(s) from {len(sources)} package(s)[/green]")

        logger.info("uninstall finished")
