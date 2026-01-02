# TODO: put a docstring here
# TODO: I'm using click, should I convert to typer?

import pathlib
import sys

import click
from loguru import logger

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
            for source_package, plan in plans:
                execute_plan(source_package, destination_root, plan)
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

        for source_package, plan in plans:
            execute_plan(source_package, destination_root, plan)
    logger.info("uninstall finished")
