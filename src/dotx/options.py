"""
This module provides convenience functions for accessing user-data on the associated context.

Note: typer is built on click, so we use click.Context for type annotations.
"""

from typing import Any

import click


def set_option(option: str, value: Any, ctx: click.Context | None = None) -> bool:
    """
    Set an option value in the Typer context.

    Stores arbitrary values in the context object dictionary for later retrieval.
    Creates the context.obj dictionary if it doesn't exist.
    """
    if ctx is None:
        # Typer uses click under the hood, so we can use click's get_current_context
        ctx = click.get_current_context()
    if ctx is not None:
        if ctx.obj is None:
            ctx.obj = {}
        ctx.obj[option] = value
        return True
    return False


def get_option(option: str, default_for_option: Any = None, ctx: click.Context | None = None) -> Any:
    """
    Get an option value from the context.

    Return type is Any because it depends on what option is requested.
    Returns the default_for_option if the option is not found.
    """
    if ctx is None:
        # Typer uses click under the hood, so we can use click's get_current_context
        ctx = click.get_current_context()
    if ctx is not None and ctx.obj is not None and option in ctx.obj:
        return ctx.obj[option]
    return default_for_option


def is_verbose_mode(ctx: click.Context | None = None) -> bool:
    """Check if verbose mode is enabled."""
    return get_option("VERBOSE", False, ctx)


def is_debug_mode(ctx: click.Context | None = None) -> bool:
    """Check if debug mode is enabled."""
    return get_option("DEBUG", False, ctx)


def is_dry_run(ctx: click.Context | None = None) -> bool:
    """Check if dry-run mode is enabled."""
    return get_option("DRYRUN", True, ctx)
