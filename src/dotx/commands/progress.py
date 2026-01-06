"""Progress display utilities for commands."""

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from dotx.plan import Action, Plan, execute_plan, extract_plan


def execute_plans_with_progress(
    plans: list[tuple[Path, Plan]],
    target_path: Path,
    actions: set[Action],
    operation: str,
    console: Console,
    verbose: bool,
    db,
) -> None:
    """
    Execute plans with progress display (verbose or progress bar).

    Args:
        plans: List of (source_package, plan) tuples
        target_path: Target directory for installation
        actions: Set of actions to track for progress
        operation: Operation name (e.g., "Installing", "Uninstalling")
        console: Rich console for output
        verbose: Whether to show verbose output
        db: Database connection for recording installations
    """
    if verbose:
        # Verbose: show each file
        for source_package, plan in plans:
            console.print(f"[cyan]{operation} {source_package.name}...[/cyan]")
            for node in extract_plan(plan, actions):
                console.print(f"  {node.relative_destination_path}")
            execute_plan(source_package, target_path, plan, db)
    else:
        # Default: show progress bar
        total_actions = sum(len(extract_plan(plan, actions)) for _, plan in plans)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"{operation}...", total=total_actions)
            for source_package, plan in plans:
                progress.update(task, description=f"{operation} {source_package.name}...")
                execute_plan(source_package, target_path, plan, db)
                progress.advance(task, len(extract_plan(plan, actions)))
