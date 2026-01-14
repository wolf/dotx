"""Install command for dotx CLI."""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console

from dotx.commands.progress import execute_plans_with_progress
from dotx.database import InstallationDB
from dotx.install import plan_install
from dotx.options import is_dry_run, is_verbose_mode
from dotx.plan import Action, Plan, extract_plan, log_extracted_plan


def register_command(app: typer.Typer):
    """Register the install command with the Typer app."""

    @app.command()
    def install(
        ctx: typer.Context,
        sources: Annotated[
            list[Path],
            typer.Argument(
                help="Source package directories to install",
                exists=True,
                file_okay=False,
                dir_okay=True,
                readable=True,
            ),
        ],
    ):
        """Install source packages to target directory."""
        logger.info("install starting")
        console = Console()
        verbose = is_verbose_mode(ctx)

        # Get target from options
        target_path = Path(ctx.obj.get("TARGET", Path.home())) if ctx.obj else Path.home()

        if sources:
            plans: list[tuple[Path, Plan]] = []
            for source_package in sources:
                plan: Plan = plan_install(source_package, target_path)
                log_extracted_plan(
                    plan,
                    description=f"Actual plan to install {source_package}",
                    actions_to_extract={Action.LINK, Action.CREATE},
                )
                plans.append((source_package, plan))

            can_install = True
            for source_package, plan in plans:
                failures = extract_plan(plan, {Action.FAIL})
                if failures:
                    can_install = False
                    console.print(
                        f"[red]✗ Error: can't install {source_package.name} - conflicts detected:[/red]"
                    )
                    for plan_node in failures:
                        dest_path = target_path / plan_node.relative_destination_path
                        if dest_path.is_symlink():
                            try:
                                link_target = dest_path.readlink()
                                console.print(f"  {dest_path} [dim](symlink → {link_target})[/dim]")
                            except OSError:
                                console.print(f"  {dest_path} [dim](broken symlink)[/dim]")
                        else:
                            console.print(f"  {dest_path} [dim](existing file)[/dim]")
                    console.print()

            if can_install:
                # Open database and execute all plans with progress
                with InstallationDB() as db:
                    execute_plans_with_progress(
                        plans,
                        target_path,
                        {Action.LINK, Action.CREATE},
                        "Installing",
                        console,
                        verbose,
                        db,
                    )

                # Show summary
                total_files = sum(
                    len(extract_plan(plan, {Action.LINK}))
                    for _, plan in plans
                )
                total_dirs = sum(
                    len(extract_plan(plan, {Action.CREATE}))
                    for _, plan in plans
                )

                summary_parts = []
                if total_files:
                    summary_parts.append(f"{total_files} file(s)")
                if total_dirs:
                    summary_parts.append(f"{total_dirs} dir(s)")

                if summary_parts:
                    summary = " and ".join(summary_parts)
                    if is_dry_run(ctx):
                        console.print(f"\n[yellow][DRY RUN] Would install {summary} from {len(sources)} package(s)[/yellow]")
                    else:
                        console.print(f"\n[green]✓ Installed {summary} from {len(sources)} package(s)[/green]")
                else:
                    # Empty package(s) - nothing to install
                    if is_dry_run(ctx):
                        console.print(f"\n[yellow][DRY RUN] Would install nothing from {len(sources)} package(s) (nothing to record in database)[/yellow]")
                    else:
                        console.print(f"\n[green]✓ Installed nothing from {len(sources)} package(s) (nothing to record in database)[/green]")
            else:
                console.print("[red]✗ Refusing to install - conflicts detected[/red]")

        logger.info("install finished")
