import logging
import pathlib

import click

from dotfiles.install import plan_install
from dotfiles.options import get_option
from dotfiles.plan import Action, Plan, execute_plan, extract_plan, log_extracted_plan


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
@click.option("--dry-run/--no-dry-run", default=True, help="Just echo; don't actually (un)install.")
@click.pass_context
def cli(ctx, debug, verbose, log, target, dry_run):
    """Manage a link farm: (un)install groups of links from "source packages"."""
    ctx.obj = {"DEBUG": debug, "VERBOSE": verbose, "TARGET": target, "DRYRUN": dry_run}
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

    if destination_root is None:
        click.echo("Error: no target directory")
        return 1

    if sources:
        plans: list[(pathlib.Path, Plan)] = []
        for source_package in sources:
            logging.info(f"Planning install of source package: {source_package}")
            plan: Plan = plan_install(source_package, destination_root, [".mypy_cache"])
            log_extracted_plan(plan, description="Actual", actions_to_extract={Action.LINK, Action.UNLINK, Action.CREATE})
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
    if sources:
        click.echo("To be uninstalled:")
        for path in sources:
            click.echo(f"\t{str(path)}")


@cli.command()
@click.pass_context
def debug(ctx):
    """Test some things that require a click.Context"""
    import dotfiles.options

    should_be_debug = False
    should_be_verbose = False
    should_be_dry_run = False
    if ctx is not None and ctx.obj is not None:
        should_be_debug = "DEBUG" in ctx.obj and ctx.obj["DEBUG"]
        should_be_verbose = "VERBOSE" in ctx.obj and ctx.obj["VERBOSE"]
        should_be_dry_run = "DRYRUN" in ctx.obj and ctx.obj["DRYRUN"]

    is_debug = dotfiles.options.is_debug_mode()
    is_verbose = dotfiles.options.is_verbose_mode()
    is_dry_run = dotfiles.options.is_dry_run()

    if is_debug != should_be_debug:
        click.echo(f"Should be debug is {should_be_debug}, but debugging is actually {is_debug}")
    if is_verbose != should_be_verbose:
        click.echo(f"Should be verbose is {should_be_verbose}, but debugging is actually {is_verbose}")
    if is_dry_run != should_be_dry_run:
        click.echo(f"Should be dry-run is {should_be_dry_run}, but debugging is actually {is_dry_run}")
