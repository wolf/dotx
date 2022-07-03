import click


def get_option(mode: str, default_for_mode=None):
    ctx = click.get_current_context()
    result = default_for_mode
    if ctx is not None and ctx.obj is not None and mode in ctx.obj:
        result = ctx.obj[mode]
    return result


def is_verbose_mode() -> bool:
    return get_option("VERBOSE", False)


def is_debug_mode() -> bool:
    return get_option("DEBUG", False)


def is_dry_run() -> bool:
    return get_option("DRYRUN", True)
