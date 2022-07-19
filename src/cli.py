import logging
import pathlib
from typing import Tuple

import click

from dotx.install import plan_install
from dotx.uninstall import plan_uninstall
from dotx.options import get_option
from dotx.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.option("--verbose/--quiet", default=False)
@click.option(
    "--log",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, writable=True, readable=True, path_type=pathlib.Path),
    help="Where to write the log (defaults to stderr)",
)
@click.option(
    "--target",
    envvar="HOME",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True, readable=True, path_type=pathlib.Path),
    help="Where to install (defaults to $HOME)",
)
@click.option("--dry-run/--no-dry-run", default=False, help="Just echo; don't actually (un)install.")
@click.option("-i", "--ignore", type=str, multiple=True, help="a pattern to exclude from installation")
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    verbose: bool,
    log: pathlib.Path,
    target: pathlib.Path,
    dry_run: bool,
    ignore: Tuple[str, ...],
):
    """Manage a link farm: (un)install groups of links from "source packages"."""
    if ignore is not None:
        ignore = list(ignore)
    ctx.obj = {"DEBUG": debug, "VERBOSE": verbose, "TARGET": target, "DRYRUN": dry_run, "IGNORE": ignore}
    log_level = logging.DEBUG if debug else logging.WARNING
    if log is None:
        logging.basicConfig(format="%(asctime)s:%(levelname)s:%(message)s", level=log_level)
    else:
        logging.basicConfig(filename=log, format="%(asctime)s:%(levelname)s:%(message)s", level=log_level)
    logging.info(ctx.obj)


@cli.command()
@click.argument(
    "sources",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
)
@click.pass_context
def install(ctx, sources):
    """install [source-package...]"""
    logging.info("install starting")
    destination_root = get_option("TARGET")

    if sources:
        plans: list[(pathlib.Path, Plan)] = []
        for source_package in sources:
            plan: Plan = plan_install(source_package, destination_root, get_option("IGNORE"))
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
                click.echo(f"Error: can't install {source_package} because it would overwrite:")
                for plan_node in failures:
                    click.echo(f"{destination_root / plan_node.relative_destination_path}")
                click.echo()

        if can_install:
            for source_package, plan in plans:
                execute_plan(source_package, destination_root, plan)
        else:
            click.echo("Refusing to install anything because of previous failures.")
    logging.info("install finished")


@cli.command()
@click.argument(
    "sources",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
)
@click.pass_context
def uninstall(ctx, sources):
    """uninstall [source-package...]"""
    logging.info("uninstall starting")
    destination_root = get_option("TARGET")

    if sources:
        plans: list[(pathlib.Path, Plan)] = []
        for source_package in sources:
            plan: Plan = plan_uninstall(source_package, destination_root, get_option("IGNORE"))
            log_extracted_plan(
                plan, description=f"Actual plan to uninstall {source_package}", actions_to_extract={Action.UNLINK}
            )
            plans.append((source_package, plan))

        for source_package, plan in plans:
            execute_plan(source_package, destination_root, plan)
    logging.info("uninstall finished")


@cli.command()
@click.pass_context
def debug(ctx):
    """Test some things that require a click.Context"""
    import dotx.options

    should_be_debug = False
    should_be_verbose = False
    should_be_dry_run = False
    if ctx is not None and ctx.obj is not None:
        should_be_debug = "DEBUG" in ctx.obj and ctx.obj["DEBUG"]
        should_be_verbose = "VERBOSE" in ctx.obj and ctx.obj["VERBOSE"]
        should_be_dry_run = "DRYRUN" in ctx.obj and ctx.obj["DRYRUN"]

    is_debug = dotx.options.is_debug_mode()
    is_verbose = dotx.options.is_verbose_mode()
    is_dry_run = dotx.options.is_dry_run()

    if is_debug != should_be_debug:
        click.echo(f"Should be debug is {should_be_debug}, but debugging is actually {is_debug}")
    if is_verbose != should_be_verbose:
        click.echo(f"Should be verbose is {should_be_verbose}, but debugging is actually {is_verbose}")
    if is_dry_run != should_be_dry_run:
        click.echo(f"Should be dry-run is {should_be_dry_run}, but debugging is actually {is_dry_run}")
