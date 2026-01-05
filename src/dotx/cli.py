"""
Command-line interface for dotx.

This module defines the CLI app structure and global options. Individual commands
are defined in the commands subpackage.
"""

import sys
from pathlib import Path
from typing import Annotated, Optional

import click
import typer
from loguru import logger

from dotx import __version__, __homepage__
from dotx.options import set_option

# Create the Typer app
app = typer.Typer(
    help="Manage a link farm: (un)install groups of links from source packages.",
    no_args_is_help=True,
    epilog=f"dotx version {__version__} | {__homepage__}",
)


def version_callback(value: bool):
    """Handle --version flag."""
    if value:
        typer.echo(f"dotx version {__version__}")
        raise typer.Exit()


def configure_logging(debug: bool, verbose: bool, log: Optional[Path]):
    """Configure logging based on CLI options."""
    logger.remove()  # Remove default handler

    # Determine log level
    if debug:
        level = "DEBUG"
    elif verbose:
        level = "INFO"
    else:
        level = "WARNING"

    # Add handler
    if log:
        logger.add(log, level=level)
    else:
        logger.add(sys.stderr, level=level)


@app.callback()
def main(
    ctx: click.Context,
    debug: Annotated[
        bool,
        typer.Option("--debug/--no-debug", help="Enable debug logging"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose/--quiet", help="Enable verbose output / suppress output"),
    ] = False,
    log: Annotated[
        Optional[Path],
        typer.Option(help="Where to write the log (defaults to stderr)"),
    ] = None,
    target: Annotated[
        Optional[Path],
        typer.Option(
            help="Where to install (defaults to $HOME)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", help="Just echo; don't actually (un)install"),
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
):
    """
    Manage a link farm: (un)install groups of links from source packages.

    Global options like --debug, --verbose, and --target apply to all commands.
    """
    configure_logging(debug, verbose, log)

    # Store options in context for commands to access
    ctx.ensure_object(dict)
    if target:
        ctx.obj["TARGET"] = target
        set_option("TARGET", target, ctx)

    # Set global options
    set_option("DEBUG", debug, ctx)
    set_option("VERBOSE", verbose, ctx)
    set_option("DRYRUN", dry_run, ctx)

    if log:
        set_option("LOG", log, ctx)


# Register commands from submodules
from dotx.commands import install_cmd, uninstall_cmd, database, path_cmd

install_cmd.register_command(app)
uninstall_cmd.register_command(app)
database.register_commands(app)
path_cmd.register_commands(app)


def cli():
    """Entry point for the CLI."""
    app()
