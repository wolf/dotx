"""This module provides convenience functions for accessing user-data on the associated `click.Context`."""


import click


def set_option(option: str, value) -> bool:
    ctx = click.get_current_context()
    if ctx is not None:
        if ctx.obj is None:
            ctx.obj = {}
        ctx.obj[option] = value
        return True
    return False


def get_option(option: str, default_for_option=None):
    ctx = click.get_current_context()
    if ctx is not None and ctx.obj is not None and option in ctx.obj:
        return ctx.obj[option]
    return default_for_option


def is_verbose_mode() -> bool:
    return get_option("VERBOSE", False)


def is_debug_mode() -> bool:
    return get_option("DEBUG", False)


def is_dry_run() -> bool:
    return get_option("DRYRUN", True)
