"""
Command-line interface for dotx.

This module defines the CLI commands for managing dotfile installations using Typer.
The main commands are:
- install: Create symlinks from source packages to target directory
- uninstall: Remove symlinks for source packages
- list: Show all installed packages
- verify: Check installation integrity
- show: Display detailed package information
- sync: Rebuild database from filesystem

Each command supports common options like --debug, --verbose, --dry-run, and --target.
The installation database tracks which packages have installed which files.
"""

import sys
from pathlib import Path
from typing import Annotated, Optional

import click
import typer
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from dotx import __version__, __homepage__
from dotx.database import InstallationDB
from dotx.install import plan_install
from dotx.options import set_option, is_verbose_mode
from dotx.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan
from dotx.uninstall import plan_uninstall

# Create the Typer app
app = typer.Typer(
    help="Manage a link farm: (un)install groups of links from source packages.",
    no_args_is_help=True,
    epilog=f"dotx version {__version__} | {__homepage__}",
)


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        typer.echo(f"dotx version {__version__}")
        raise typer.Exit()


def configure_logging(debug: bool, verbose: bool, log: Optional[Path]):
    """Configure loguru logging based on command-line options."""
    logger.remove()  # Remove default handler
    log_level = "DEBUG" if debug else "WARNING"

    if log is None:
        logger.add(
            sys.stderr,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        )
    else:
        logger.add(
            log,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        )


@app.callback()
def main(
    ctx: click.Context,
    debug: Annotated[bool, typer.Option("--debug/--no-debug")] = False,
    verbose: Annotated[bool, typer.Option("--verbose/--quiet")] = False,
    log: Annotated[
        Optional[Path],
        typer.Option(
            help="Where to write the log (defaults to stderr)",
            exists=False,
            file_okay=True,
            dir_okay=False,
            writable=True,
            readable=True,
        ),
    ] = None,
    target: Annotated[
        Path,
        typer.Option(
            envvar="HOME",
            help="Where to install (defaults to $HOME)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
        ),
    ] = Path.home(),
    dry_run: Annotated[
        bool, typer.Option("--dry-run/--no-dry-run", help="Just echo; don't actually (un)install.")
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
):
    """Manage a link farm: (un)install groups of links from "source packages"."""
    # Store options in context for access by commands
    set_option("DEBUG", debug, ctx)
    set_option("VERBOSE", verbose, ctx)
    set_option("TARGET", target, ctx)
    set_option("DRYRUN", dry_run, ctx)

    # Configure logging
    configure_logging(debug, verbose, log)

    logger.info(f"Options: debug={debug}, verbose={verbose}, target={target}, dry_run={dry_run}")


@app.command()
def install(
    ctx: click.Context,
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


@app.command()
def uninstall(
    ctx: click.Context,
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


@app.command(name="list")
def list_installed(
    as_commands: Annotated[
        bool,
        typer.Option("--as-commands", help="Output as reinstall commands instead of table"),
    ] = False,
):
    """List all installed packages."""
    logger.info("list starting")
    console = Console()

    with InstallationDB() as db:
        packages = db.get_all_packages()

        if not packages:
            console.print("[yellow]No packages installed.[/yellow]")
            return

        if as_commands:
            # Output as dotx install commands (plain text, no formatting)
            for pkg in packages:
                typer.echo(f"dotx install {pkg['package_name']}")
        else:
            # Output as rich table
            table = Table(title="Installed Packages", show_header=True, header_style="bold cyan")
            table.add_column("Package", style="cyan", no_wrap=True)
            table.add_column("Files", justify="right", style="magenta")
            table.add_column("Last Install", style="green")

            for pkg in packages:
                package_name = Path(pkg["package_name"]).name
                file_count = str(pkg["file_count"])
                latest = (
                    pkg["latest_install"][:19]
                    if pkg["latest_install"]
                    else "[dim]unknown[/dim]"
                )
                table.add_row(package_name, file_count, latest)

            console.print()
            console.print(table)
            console.print(f"\n[bold]Total: {len(packages)} package(s)[/bold]\n")

    logger.info("list finished")


@app.command()
def verify(
    package: Annotated[
        Optional[Path],
        typer.Argument(
            help="Package to verify (all packages if not specified)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ] = None,
):
    """Verify installations against filesystem."""
    logger.info("verify starting")
    console = Console()

    with InstallationDB() as db:
        if package:
            # Verify specific package
            packages_to_verify = [package]
        else:
            # Verify all packages
            all_packages = db.get_all_packages()
            packages_to_verify = [
                Path(pkg["package_name"]) for pkg in all_packages
            ]

        if not packages_to_verify:
            console.print("[yellow]No packages to verify.[/yellow]")
            return

        total_issues = 0
        for pkg in packages_to_verify:
            issues = db.verify_installations(pkg)
            if issues:
                console.print(f"\n[bold cyan]{pkg.name}:[/bold cyan]")
                for issue in issues:
                    console.print(f"  [red]✗[/red] {issue['target_path']}")
                    console.print(f"    [dim]Issue: {issue['issue']}[/dim]")
                    console.print(f"    [dim]Expected: {issue['link_type']}[/dim]")
                total_issues += len(issues)

        if total_issues == 0:
            console.print("[green]✓ All installations verified successfully.[/green]")
        else:
            console.print(f"\n[yellow]⚠ Found {total_issues} issue(s).[/yellow]")

    logger.info("verify finished")


@app.command()
def show(
    package: Annotated[
        Path,
        typer.Argument(
            help="Package to show details for",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ],
):
    """Show detailed installation information for a package."""
    logger.info("show starting")
    console = Console()

    with InstallationDB() as db:
        installations = db.get_installations(package)

        if not installations:
            console.print(f"[yellow]No installations found for {package.name}[/yellow]")
            return

        # Create info panel
        info = f"[bold cyan]Package:[/bold cyan] {package}\n"
        info += f"[bold cyan]Installed files:[/bold cyan] {len(installations)}"

        panel = Panel(info, title="Package Information", border_style="cyan")
        console.print()
        console.print(panel)

        # Create table for installations
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Target Path", style="cyan", no_wrap=False, overflow="fold")
        table.add_column("Type", style="yellow")
        table.add_column("Installed At", style="green")

        for install in installations:
            table.add_row(
                str(install['target_path']),
                install['link_type'],
                install['installed_at'][:19] if install['installed_at'] else "unknown"
            )

        console.print()
        console.print(table)
        console.print()

    logger.info("show finished")


def _scan_symlinks(path: Path, max_depth: int, progress: Progress, task_id) -> list[tuple[Path, bool]]:
    """
    Scan a directory for symlinks up to a maximum depth.

    Returns list of (symlink_path, is_dir) tuples.
    """
    symlinks = []

    def _walk_limited(directory: Path, current_depth: int):
        """Recursively walk directory up to max_depth."""
        if current_depth > max_depth:
            return

        try:
            for item in directory.iterdir():
                # Update progress
                progress.update(task_id, advance=1)

                if item.is_symlink():
                    is_dir = item.is_dir()  # Check if symlink points to directory
                    symlinks.append((item, is_dir))
                    # Don't descend into symlinked directories
                    continue

                # Recurse into regular directories
                if item.is_dir() and not item.is_symlink():
                    _walk_limited(item, current_depth + 1)

        except (PermissionError, OSError) as e:
            logger.debug(f"Skipping {directory}: {e}")

    _walk_limited(path, 0)
    return symlinks


@app.command()
def sync(
    ctx: click.Context,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be added without modifying the database"),
    ] = False,
    max_depth: Annotated[
        Optional[int],
        typer.Option(help="Maximum depth to scan (default: 1 for home, 3 for config)"),
    ] = None,
    scan_paths: Annotated[
        Optional[list[Path]],
        typer.Option(help="Additional paths to scan"),
    ] = None,
    simple: Annotated[
        bool,
        typer.Option(help="Simple scan: only home directory depth 1, skip ~/.config"),
    ] = False,
):
    """
    Rebuild database from filesystem (scan for existing symlinks).

    By default, scans:
    - Top-level of home directory (depth=1)
    - All of ~/.config (depth=3)

    Use --simple to only scan home directory at depth 1.
    Use --max-depth to override default depth for all paths.
    Use --scan-paths to add additional directories to scan.
    """
    logger.info("sync starting")
    console = Console()

    # Get target from options
    target_path = Path(ctx.obj.get("TARGET", Path.home())) if ctx.obj else Path.home()

    # Determine scan strategy
    scan_configs = []

    if simple:
        # Simple mode: just top-level of home
        scan_configs.append((target_path, max_depth or 1))
    else:
        # Smart mode: top-level home + full ~/.config
        scan_configs.append((target_path, max_depth or 1))
        config_path = target_path / ".config"
        if config_path.exists() and config_path.is_dir():
            scan_configs.append((config_path, max_depth or 3))

    # Add any user-specified paths
    if scan_paths:
        for path in scan_paths:
            scan_configs.append((path, max_depth or 3))

    # Scan filesystem for symlinks with progress
    symlinks = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        scan_task = progress.add_task("Scanning for symlinks...", total=None)

        for scan_path, depth in scan_configs:
            progress.update(scan_task, description=f"Scanning {scan_path.name}...")
            symlinks.extend(_scan_symlinks(scan_path, depth, progress, scan_task))

    console.print(f"[green]✓[/green] Found {len(symlinks)} symlink(s)")

    if not symlinks:
        console.print("[yellow]No symlinks found.[/yellow]")
        logger.info("sync finished - no symlinks found")
        return

    # Group symlinks by their resolved source parent directory (package)
    packages = {}
    unknown = []

    for link_path, is_dir in symlinks:
        try:
            # Resolve the symlink to find the actual source
            resolved = link_path.resolve(strict=True)

            # Try to find a reasonable package root
            # Assume package is parent directory of the resolved path
            # This is a heuristic - might need refinement
            if resolved.parent.exists():
                package_root = resolved.parent
                if package_root not in packages:
                    packages[package_root] = []
                packages[package_root].append((link_path, resolved, is_dir))
            else:
                unknown.append((link_path, resolved, is_dir))
        except (OSError, RuntimeError) as e:
            logger.warning(f"Failed to resolve symlink {link_path}: {e}")
            unknown.append((link_path, None, is_dir))

    # Show what was found
    console.print(f"\n[bold]Discovered {len(packages)} potential package(s):[/bold]")
    for package_root, links in packages.items():
        console.print(f"  [cyan]{package_root}[/cyan]")
        console.print(f"    {len(links)} symlink(s)")

    if unknown:
        console.print(f"  [yellow]Unknown/broken: {len(unknown)} symlink(s)[/yellow]")

    if dry_run:
        console.print("\n[yellow]Dry run - no database changes made.[/yellow]")
        logger.info("sync finished - dry run")
        return

    # Ask for confirmation
    console.print("\n[bold]This will rebuild the database with the discovered installations.[/bold]")
    if not typer.confirm("Continue?"):
        console.print("[yellow]Cancelled.[/yellow]")
        logger.info("sync finished - cancelled by user")
        return

    # Open database and record installations
    with InstallationDB() as db:
        total_recorded = 0

        for package_root, links in packages.items():
            for link_path, resolved, is_dir in links:
                # Determine link type
                if is_dir:
                    link_type = "directory"
                else:
                    link_type = "file"

                # Record in database
                db.record_installation(package_root, link_path, link_type)
                total_recorded += 1
                logger.debug(f"Recorded {link_path} -> {package_root}")

        console.print(f"\n[green]✓ Recorded {total_recorded} installation(s) in database.[/green]")

    logger.info("sync finished")


def cli():
    """Entry point for the CLI."""
    app()
