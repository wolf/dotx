"""Uninstall command for dotx CLI."""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console

from dotx.commands.progress import execute_plans_with_progress
from dotx.database import InstallationDB
from dotx.options import is_dry_run, is_verbose_mode
from dotx.plan import Action, Plan, extract_plan, log_extracted_plan
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

            # Open database and execute all plans with progress
            with InstallationDB() as db:
                execute_plans_with_progress(
                    plans,
                    target_path,
                    {Action.UNLINK},
                    "Uninstalling",
                    console,
                    verbose,
                    db,
                )

            # Show summary
            total_removed = sum(
                len(extract_plan(plan, {Action.UNLINK}))
                for _, plan in plans
            )
            if is_dry_run(ctx):
                console.print(f"\n[yellow][DRY RUN] Would remove {total_removed} symlink(s) from {len(sources)} package(s)[/yellow]")
            else:
                console.print(f"\n[green]✓ Removed {total_removed} symlink(s) from {len(sources)} package(s)[/green]")

        logger.info("uninstall finished")
