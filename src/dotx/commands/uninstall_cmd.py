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


def _uninstall_from_database(
    package_path: Path,
    db: InstallationDB,
    console: Console,
    dry_run: bool,
    verbose: bool,
) -> int:
    """
    Uninstall a package using database records when source directory is missing.

    Returns the number of symlinks removed.
    """
    package_root = package_path.parent
    package_name = package_path.name

    installations = db.get_installations(package_root, package_name)

    if not installations:
        console.print(f"[yellow]No installations found for {package_name}[/yellow]")
        return 0

    removed_count = 0

    for entry in installations:
        target_path = Path(entry["target_path"])

        if dry_run:
            if target_path.is_symlink():
                console.print(f"  rm {target_path}")
                removed_count += 1
            elif verbose:
                console.print(f"  [dim]skip (not a symlink): {target_path}[/dim]")
        else:
            if target_path.is_symlink():
                try:
                    target_path.unlink()
                    db.remove_installation(target_path)
                    removed_count += 1
                    if verbose:
                        console.print(f"  Removed: {target_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove {target_path}: {e}")
            else:
                # Not a symlink - just remove from database
                db.remove_installation(target_path)
                if verbose:
                    console.print(f"  [dim]Cleaned db entry (not a symlink): {target_path}[/dim]")

    return removed_count


def register_command(app: typer.Typer):
    """Register the uninstall command with the Typer app."""

    @app.command()
    def uninstall(
        ctx: typer.Context,
        sources: Annotated[
            list[Path],
            typer.Argument(
                help="Source package directories to uninstall (can be deleted)",
            ),
        ],
    ):
        """
        Uninstall source packages from target directory.

        If the source package directory still exists, uninstalls by scanning it.
        If the source has been deleted, uninstalls using database records.
        """
        logger.info("uninstall starting")
        console = Console()
        verbose = is_verbose_mode(ctx)
        dry_run = is_dry_run(ctx)

        # Get target from options
        target_path = Path(ctx.obj.get("TARGET", Path.home())) if ctx.obj else Path.home()

        if not sources:
            logger.info("uninstall finished (no sources)")
            return

        # Partition sources using set math
        sources_set = set(sources)
        existing_sources = {s for s in sources_set if s.exists() and s.is_dir()}
        missing_sources = sources_set - existing_sources

        total_removed = 0

        # Handle existing sources with plan-based uninstall
        if existing_sources:
            plans: list[tuple[Path, Plan]] = []
            for source_package in existing_sources:
                plan: Plan = plan_uninstall(source_package, target_path)
                log_extracted_plan(
                    plan,
                    description=f"Actual plan to uninstall {source_package}",
                    actions_to_extract={Action.UNLINK},
                )
                plans.append((source_package, plan))

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

            total_removed += sum(
                len(extract_plan(plan, {Action.UNLINK}))
                for _, plan in plans
            )

        # Handle missing sources with database-based uninstall
        if missing_sources:
            if dry_run:
                console.print("\n[yellow][DRY RUN] Would execute the equivalent of:[/yellow]")

            with InstallationDB() as db:
                for source_package in missing_sources:
                    if verbose or dry_run:
                        console.print(f"\n[cyan]Uninstalling {source_package.name} (source deleted)...[/cyan]")

                    removed = _uninstall_from_database(
                        source_package, db, console, dry_run, verbose
                    )
                    total_removed += removed

        # Show summary
        if dry_run:
            console.print(f"\n[yellow][DRY RUN] Would remove {total_removed} symlink(s) from {len(sources)} package(s)[/yellow]")
        else:
            console.print(f"\n[green]✓ Removed {total_removed} symlink(s) from {len(sources)} package(s)[/green]")

        logger.info("uninstall finished")
