"""Install command for dotx CLI."""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from dotx.database import InstallationDB
from dotx.install import plan_install
from dotx.options import is_verbose_mode
from dotx.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan


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
                        f"[red]✗ Error: can't install {source_package.name} - would overwrite:[/red]"
                    )
                    for plan_node in failures:
                        console.print(f"  {target_path / plan_node.relative_destination_path}")
                    console.print()

            if can_install:
                # Count total actions
                total_actions = sum(
                    len(extract_plan(plan, {Action.LINK, Action.CREATE}))
                    for _, plan in plans
                )

                # Open database and execute all plans with progress
                with InstallationDB() as db:
                    if verbose:
                        # Verbose: show each file
                        for source_package, plan in plans:
                            console.print(f"[cyan]Installing {source_package.name}...[/cyan]")
                            for node in extract_plan(plan, {Action.LINK, Action.CREATE}):
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
                            task = progress.add_task("Installing...", total=total_actions)
                            for source_package, plan in plans:
                                progress.update(task, description=f"Installing {source_package.name}...")
                                execute_plan(source_package, target_path, plan, db)
                                progress.advance(task, len(extract_plan(plan, {Action.LINK, Action.CREATE})))

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

                summary = " and ".join(summary_parts) if summary_parts else "nothing"
                console.print(f"\n[green]✓ Installed {summary} from {len(sources)} package(s)[/green]")
            else:
                console.print("[red]✗ Refusing to install - conflicts detected[/red]")

        logger.info("install finished")
