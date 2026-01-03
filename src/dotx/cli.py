"""
Command-line interface for dotx.

This module defines the CLI commands for managing dotfile installations using Click.
The main commands are:
- install: Create symlinks from source packages to target directory
- uninstall: Remove symlinks for source packages
- list: Show all installed packages
- verify: Check installation integrity
- show: Display detailed package information
- sync: Rebuild database from filesystem (placeholder)

Each command supports common options like --debug, --verbose, --dry-run, and --target.
The installation database tracks which packages have installed which files.
"""

import pathlib
import sys

import click
from loguru import logger

from dotx.database import InstallationDB
from dotx.install import plan_install
from dotx.uninstall import plan_uninstall
from dotx.options import get_option
from dotx.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.option("--verbose/--quiet", default=False)
@click.option(
    "--log",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=False,
        writable=True,
        readable=True,
        path_type=pathlib.Path,
    ),
    help="Where to write the log (defaults to stderr)",
)
@click.option(
    "--target",
    envvar="HOME",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        path_type=pathlib.Path,
    ),
    help="Where to install (defaults to $HOME)",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    help="Just echo; don't actually (un)install.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    verbose: bool,
    log: pathlib.Path,
    target: pathlib.Path,
    dry_run: bool,
):
    """Manage a link farm: (un)install groups of links from "source packages"."""
    ctx.obj = {
        "DEBUG": debug,
        "VERBOSE": verbose,
        "TARGET": target,
        "DRYRUN": dry_run,
    }

    # Configure loguru
    logger.remove()  # Remove default handler
    log_level = "DEBUG" if debug else "WARNING"

    if log is None:
        logger.add(sys.stderr, level=log_level, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")
    else:
        logger.add(log, level=log_level, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")

    logger.info(ctx.obj)


@cli.command()
@click.argument(
    "sources",
    nargs=-1,
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=pathlib.Path,
    ),
)
@click.pass_context
def install(ctx, sources):
    """install [source-package...]"""
    logger.info("install starting")
    destination_root = pathlib.Path(get_option("TARGET"))

    if sources:
        plans: list[tuple[pathlib.Path, Plan]] = []
        for source_package in sources:
            plan: Plan = plan_install(source_package, destination_root)
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
                click.echo(
                    f"Error: can't install {source_package} because it would overwrite:"
                )
                for plan_node in failures:
                    click.echo(
                        f"{destination_root / plan_node.relative_destination_path}"
                    )
                click.echo()

        if can_install:
            # Open database and execute all plans
            with InstallationDB() as db:
                for source_package, plan in plans:
                    execute_plan(source_package, destination_root, plan, db)
        else:
            click.echo("Refusing to install anything because of previous failures.")
    logger.info("install finished")


@cli.command()
@click.argument(
    "sources",
    nargs=-1,
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=pathlib.Path,
    ),
)
@click.pass_context
def uninstall(ctx, sources):
    """uninstall [source-package...]"""
    logger.info("uninstall starting")
    destination_root = pathlib.Path(get_option("TARGET"))

    if sources:
        plans: list[tuple[pathlib.Path, Plan]] = []
        for source_package in sources:
            plan: Plan = plan_uninstall(source_package, destination_root)
            log_extracted_plan(
                plan,
                description=f"Actual plan to uninstall {source_package}",
                actions_to_extract={Action.UNLINK},
            )
            plans.append((source_package, plan))

        # Open database and execute all plans
        with InstallationDB() as db:
            for source_package, plan in plans:
                execute_plan(source_package, destination_root, plan, db)
    logger.info("uninstall finished")


@cli.command(name="list")
@click.option(
    "--as-commands",
    is_flag=True,
    help="Output as reinstall commands instead of table",
)
def list_installed(as_commands):
    """List all installed packages."""
    logger.info("list starting")

    with InstallationDB() as db:
        packages = db.get_all_packages()

        if not packages:
            click.echo("No packages installed.")
            return

        if as_commands:
            # Output as dotx install commands
            for pkg in packages:
                click.echo(f"dotx install {pkg['package_name']}")
        else:
            # Output as table
            click.echo("\nInstalled Packages:")
            click.echo("-" * 80)
            click.echo(f"{'Package':<50} {'Files':<10} {'Last Install':<20}")
            click.echo("-" * 80)
            for pkg in packages:
                package_name = pathlib.Path(pkg["package_name"]).name
                file_count = pkg["file_count"]
                latest = pkg["latest_install"][:19] if pkg["latest_install"] else "unknown"
                click.echo(f"{package_name:<50} {file_count:<10} {latest:<20}")
            click.echo("-" * 80)
            click.echo(f"Total: {len(packages)} package(s)\n")

    logger.info("list finished")


@cli.command()
@click.argument(
    "package",
    required=False,
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=pathlib.Path,
    ),
)
def verify(package):
    """Verify installations against filesystem."""
    logger.info("verify starting")

    with InstallationDB() as db:
        if package:
            # Verify specific package
            packages_to_verify = [package]
        else:
            # Verify all packages
            all_packages = db.get_all_packages()
            packages_to_verify = [pathlib.Path(pkg["package_name"]) for pkg in all_packages]

        if not packages_to_verify:
            click.echo("No packages to verify.")
            return

        total_issues = 0
        for pkg in packages_to_verify:
            issues = db.verify_installations(pkg)
            if issues:
                click.echo(f"\n{pkg}:")
                for issue in issues:
                    click.echo(f"  {issue['target_path']}")
                    click.echo(f"    Issue: {issue['issue']}")
                    click.echo(f"    Expected type: {issue['link_type']}")
                total_issues += len(issues)

        if total_issues == 0:
            click.echo("✓ All installations verified successfully.")
        else:
            click.echo(f"\n⚠ Found {total_issues} issue(s).")

    logger.info("verify finished")


@cli.command()
@click.argument(
    "package",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=pathlib.Path,
    ),
)
def show(package):
    """Show detailed installation information for a package."""
    logger.info("show starting")

    with InstallationDB() as db:
        installations = db.get_installations(package)

        if not installations:
            click.echo(f"No installations found for {package}")
            return

        click.echo(f"\nPackage: {package}")
        click.echo(f"Installed files: {len(installations)}")
        click.echo("\nInstallations:")
        click.echo("-" * 80)

        for install in installations:
            click.echo(f"\n  Target: {install['target_path']}")
            click.echo(f"  Type:   {install['link_type']}")
            click.echo(f"  When:   {install['installed_at']}")

        click.echo("-" * 80)

    logger.info("show finished")


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be added without modifying the database",
)
def sync(dry_run):
    """Rebuild database from filesystem (scan for existing symlinks)."""
    logger.info("sync starting")

    destination_root = pathlib.Path(get_option("TARGET"))

    # Scan filesystem for symlinks
    symlinks = []
    for root, dirs, files in destination_root.walk():
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
        click.echo("No symlinks found in target directory.")
        logger.info("sync finished - no symlinks found")
        return

    click.echo(f"Found {len(symlinks)} symlink(s) in {destination_root}")

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
    click.echo(f"\nDiscovered {len(packages)} potential package(s):")
    for package_root, links in packages.items():
        click.echo(f"\n  {package_root}")
        click.echo(f"    {len(links)} symlink(s)")

    if unknown:
        click.echo(f"\n  Unknown/broken: {len(unknown)} symlink(s)")

    if dry_run:
        click.echo("\nDry run - no database changes made.")
        logger.info("sync finished - dry run")
        return

    # Ask for confirmation
    click.echo("\nThis will rebuild the database with the discovered installations.")
    if not click.confirm("Continue?"):
        click.echo("Cancelled.")
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

        click.echo(f"\n✓ Recorded {total_recorded} installation(s) in database.")

    logger.info("sync finished")
