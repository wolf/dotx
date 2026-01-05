"""Database-related commands for dotx CLI (list, verify, show, sync)."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from dotx.database import InstallationDB
from dotx.options import is_verbose_mode


def _format_timestamp(iso_timestamp: str | None) -> str:
    """
    Format an ISO timestamp for display.

    Converts ISO 8601 timestamp to readable format: YYYY-MM-DD HH:MM:SS
    Returns 'unknown' if timestamp is None or invalid.
    """
    if not iso_timestamp:
        return "unknown"

    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return "unknown"


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


def register_commands(app: typer.Typer):
    """Register all database commands with the Typer app."""

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
                    # Use package_root / package_name to construct install path
                    package_path = Path(pkg["package_root"]) / pkg["package_name"]
                    typer.echo(f"dotx install {package_path}")
            else:
                # Output as rich table
                table = Table(title="Installed Packages", show_header=True, header_style="bold cyan")
                table.add_column("Package", style="cyan", no_wrap=True)
                table.add_column("Files", justify="right", style="magenta")
                table.add_column("Last Install", style="green")

                for pkg in packages:
                    package_name = pkg["package_name"]  # Already the semantic name
                    file_count = str(pkg["file_count"])
                    latest = _format_timestamp(pkg["latest_install"])
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
                packages_to_verify = [(package.parent, package.name)]
            else:
                # Verify all packages
                all_packages = db.get_all_packages()
                packages_to_verify = [
                    (Path(pkg["package_root"]), pkg["package_name"]) for pkg in all_packages
                ]

            if not packages_to_verify:
                console.print("[yellow]No packages to verify.[/yellow]")
                return

            total_issues = 0
            for pkg_root, pkg_name in packages_to_verify:
                issues = db.verify_installations(pkg_root, pkg_name)
                if issues:
                    console.print(f"\n[bold cyan]{pkg_name}:[/bold cyan]")
                    for issue in issues:
                        console.print(f"  [red]✗[/red] {issue["target_path"]}")
                        console.print(f"    [dim]Issue: {issue["issue"]}[/dim]")
                        console.print(f"    [dim]Expected: {issue["link_type"]}[/dim]")
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

        # Extract package info
        package_root = package.parent
        package_name = package.name

        with InstallationDB() as db:
            installations = db.get_installations(package_root, package_name)

            if not installations:
                console.print(f"[yellow]No installations found for {package_name}[/yellow]")
                return

            # Create info panel
            info = f"[bold cyan]Package:[/bold cyan] {package_name}\n"
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
                    str(install["target_path"]),
                    install["link_type"],
                    _format_timestamp(install["installed_at"])
                )

            console.print()
            console.print(table)
            console.print()

        logger.info("show finished")

    @app.command()
    def sync(
        ctx: typer.Context,
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
        package_root: Annotated[
            Optional[list[Path]],
            typer.Option("--package-root", help="Only include packages under these directories (can specify multiple)"),
        ] = None,
        clean: Annotated[
            bool,
            typer.Option("--clean", help="Remove orphaned database entries (files that no longer exist)"),
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
        Use --package-root to filter packages to specific directories (recommended).
        Use --clean to remove orphaned entries (like git fetch --prune).
        """
        logger.info("sync starting")
        console = Console()
        verbose = is_verbose_mode(ctx)

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
                    package_path = resolved.parent
                    if package_path not in packages:
                        packages[package_path] = []
                    packages[package_path].append((link_path, resolved, is_dir))
                else:
                    unknown.append((link_path, resolved, is_dir))
            except (OSError, RuntimeError) as e:
                if verbose:
                    logger.warning(f"Failed to resolve symlink {link_path}: {e}")
                unknown.append((link_path, None, is_dir))

        # Filter packages by package_root if specified
        if package_root:
            # Resolve all package roots for comparison
            package_roots = [p.resolve() for p in package_root]
            filtered_packages = {}
            filtered_out = 0

            for pkg_path, links in packages.items():
                # Check if this package is under any of the specified roots
                pkg_resolved = pkg_path.resolve()
                is_under_root = any(
                    pkg_resolved == root or root in pkg_resolved.parents
                    for root in package_roots
                )

                if is_under_root:
                    filtered_packages[pkg_path] = links
                else:
                    filtered_out += len(links)
                    logger.debug(f"Filtered out package {pkg_path} (not under --package-root)")

            packages = filtered_packages

            if filtered_out > 0:
                console.print(f"[dim]Filtered out {filtered_out} symlink(s) not under --package-root[/dim]")

        # Warn if no package_root specified and database doesn't exist or is empty
        if not package_root:
            with InstallationDB() as db:
                existing_packages = db.get_all_packages()
                if not existing_packages:
                    console.print(
                        "[yellow]⚠ Warning: No --package-root specified and database is empty.[/yellow]"
                    )
                    console.print(
                        "[yellow]  Consider using --package-root to filter packages (e.g., --package-root ~/dotfiles)[/yellow]\n"
                    )

        # Show what was found
        console.print(f"\n[bold]Discovered {len(packages)} potential package(s):[/bold]")
        for package_path, links in packages.items():
            console.print(f"  [cyan]{package_path}[/cyan]")
            console.print(f"    {len(links)} symlink(s)")

        if unknown:
            console.print(f"  [yellow]Unknown/broken: {len(unknown)} symlink(s)[/yellow]")

        if dry_run:
            # Preview clean operation if requested
            if clean:
                console.print("\n[cyan]Would clean orphaned entries:[/cyan]")
                with InstallationDB() as db:
                    all_packages = db.get_all_packages()
                    total_would_clean = 0

                    for pkg_info in all_packages:
                        pkg_root = Path(pkg_info["package_root"])
                        pkg_name = pkg_info["package_name"]
                        orphaned = db.get_orphaned_entries(pkg_root, pkg_name)
                        if orphaned:
                            total_would_clean += len(orphaned)
                            console.print(f"  {pkg_name}: {len(orphaned)} orphaned entry(ies)")

                    if total_would_clean > 0:
                        console.print(f"[yellow]Would remove {total_would_clean} orphaned entry(ies).[/yellow]")
                    else:
                        console.print("[green]No orphaned entries to clean.[/green]")

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

            for package_path, links in packages.items():
                # Extract package info for database
                package_root = package_path.parent
                package_name = package_path.name

                for link_path, resolved, is_dir in links:
                    # Determine link type
                    if is_dir:
                        link_type = "directory"
                    else:
                        link_type = "file"

                    # Record in database
                    db.record_installation(package_root, package_name, package_path, link_path, link_type)
                    total_recorded += 1
                    logger.debug(f"Recorded {link_path} -> {package_name}")

            console.print(f"\n[green]✓ Recorded {total_recorded} installation(s) in database.[/green]")

            # Clean orphaned entries if requested
            if clean:
                console.print("\n[cyan]Cleaning orphaned entries...[/cyan]")
                all_packages = db.get_all_packages()
                total_cleaned = 0

                for pkg_info in all_packages:
                    pkg_root = Path(pkg_info["package_root"])
                    pkg_name = pkg_info["package_name"]
                    cleaned = db.clean_orphaned_entries(pkg_root, pkg_name)
                    if cleaned > 0:
                        total_cleaned += cleaned
                        if verbose:
                            console.print(f"  Cleaned {cleaned} orphaned entry(ies) from {pkg_name}")

                if total_cleaned > 0:
                    console.print(f"[green]✓ Removed {total_cleaned} orphaned entry(ies).[/green]")
                else:
                    console.print("[green]✓ No orphaned entries found.[/green]")

        logger.info("sync finished")
