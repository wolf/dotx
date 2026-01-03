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

from dotx import __version__
from dotx.database import InstallationDB
from dotx.install import plan_install
from dotx.options import set_option
from dotx.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan
from dotx.uninstall import plan_uninstall

# Create the Typer app
app = typer.Typer(
    help="Manage a link farm: (un)install groups of links from source packages."
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
                typer.echo(
                    f"Error: can't install {source_package} because it would overwrite:"
                )
                for plan_node in failures:
                    typer.echo(f"{target_path / plan_node.relative_destination_path}")
                typer.echo()

        if can_install:
            # Open database and execute all plans
            with InstallationDB() as db:
                for source_package, plan in plans:
                    execute_plan(source_package, target_path, plan, db)
        else:
            typer.echo("Refusing to install anything because of previous failures.")

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

        # Open database and execute all plans
        with InstallationDB() as db:
            for source_package, plan in plans:
                execute_plan(source_package, target_path, plan, db)

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

    with InstallationDB() as db:
        packages = db.get_all_packages()

        if not packages:
            typer.echo("No packages installed.")
            return

        if as_commands:
            # Output as dotx install commands
            for pkg in packages:
                typer.echo(f"dotx install {pkg['package_name']}")
        else:
            # Output as table
            typer.echo("\nInstalled Packages:")
            typer.echo("-" * 80)
            typer.echo(f"{'Package':<50} {'Files':<10} {'Last Install':<20}")
            typer.echo("-" * 80)
            for pkg in packages:
                package_name = Path(pkg["package_name"]).name
                file_count = pkg["file_count"]
                latest = (
                    pkg["latest_install"][:19]
                    if pkg["latest_install"]
                    else "unknown"
                )
                typer.echo(f"{package_name:<50} {file_count:<10} {latest:<20}")
            typer.echo("-" * 80)
            typer.echo(f"Total: {len(packages)} package(s)\n")

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
            typer.echo("No packages to verify.")
            return

        total_issues = 0
        for pkg in packages_to_verify:
            issues = db.verify_installations(pkg)
            if issues:
                typer.echo(f"\n{pkg}:")
                for issue in issues:
                    typer.echo(f"  {issue['target_path']}")
                    typer.echo(f"    Issue: {issue['issue']}")
                    typer.echo(f"    Expected type: {issue['link_type']}")
                total_issues += len(issues)

        if total_issues == 0:
            typer.echo("✓ All installations verified successfully.")
        else:
            typer.echo(f"\n⚠ Found {total_issues} issue(s).")

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

    with InstallationDB() as db:
        installations = db.get_installations(package)

        if not installations:
            typer.echo(f"No installations found for {package}")
            return

        typer.echo(f"\nPackage: {package}")
        typer.echo(f"Installed files: {len(installations)}")
        typer.echo("\nInstallations:")
        typer.echo("-" * 80)

        for install in installations:
            typer.echo(f"\n  Target: {install['target_path']}")
            typer.echo(f"  Type:   {install['link_type']}")
            typer.echo(f"  When:   {install['installed_at']}")

        typer.echo("-" * 80)

    logger.info("show finished")


@app.command()
def sync(
    ctx: click.Context,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be added without modifying the database"),
    ] = False,
):
    """Rebuild database from filesystem (scan for existing symlinks)."""
    logger.info("sync starting")

    # Get target from options
    target_path = Path(ctx.obj.get("TARGET", Path.home())) if ctx.obj else Path.home()

    # Scan filesystem for symlinks
    symlinks = []
    for root, dirs, files in target_path.walk():
        # Check if directories are symlinks
        for dirname in dirs[:]:
            dirpath = root / dirname
            if dirpath.is_symlink():
                symlinks.append((dirpath, True))  # (path, is_dir)
                # Don't descend into symlinked directories
                dirs.remove(dirname)

        # Check if files are symlinks
        for filename in files:
            filepath = root / filename
            if filepath.is_symlink():
                symlinks.append((filepath, False))  # (path, is_dir)

    if not symlinks:
        typer.echo("No symlinks found in target directory.")
        logger.info("sync finished - no symlinks found")
        return

    typer.echo(f"Found {len(symlinks)} symlink(s) in {target_path}")

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
    typer.echo(f"\nDiscovered {len(packages)} potential package(s):")
    for package_root, links in packages.items():
        typer.echo(f"\n  {package_root}")
        typer.echo(f"    {len(links)} symlink(s)")

    if unknown:
        typer.echo(f"\n  Unknown/broken: {len(unknown)} symlink(s)")

    if dry_run:
        typer.echo("\nDry run - no database changes made.")
        logger.info("sync finished - dry run")
        return

    # Ask for confirmation
    typer.echo("\nThis will rebuild the database with the discovered installations.")
    if not typer.confirm("Continue?"):
        typer.echo("Cancelled.")
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

        typer.echo(f"\n✓ Recorded {total_recorded} installation(s) in database.")

    logger.info("sync finished")


def cli():
    """Entry point for the CLI."""
    app()
