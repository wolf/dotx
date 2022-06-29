import pathlib

import click

from dotfiles.plan import Plan, debug_print_extracted_plan
from dotfiles.install import plan_install


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.option("--verbose/--quiet", default=False)
@click.option(
    "-t",
    "--target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True, readable=True, path_type=pathlib.Path),
    help="The directory to install into",
)
@click.option("--dry-run", default=True, help="Print a list of what would be done; don't actually do it.")
@click.pass_context
def cli(ctx, debug, verbose, target, dry_run):
    """Manage a link farm: install and uninstall groups of links from "source packages"."""
    ctx.obj = {"DEBUG": debug, "VERBOSE": verbose, "TARGET": target, "DRYRUN": dry_run}

    click.echo(f"Debug mode is {'on' if debug else 'off'}")
    click.echo(f"Verbose mode is {'on' if verbose else 'off'}")
    click.echo(f"Dry-run mode is {'on' if dry_run else 'off'}")
    click.echo(f"Target is {target}")


@cli.command()
@click.argument(
    "sources",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
)
@click.pass_context
def install(ctx, sources):
    """install [source-package...]"""
    if sources:
        for path in sources:
            # plan: Plan = plan_install_paths(path, ['.mypy_cache'])
            # debug_print_plan(path, plan)
            plan: Plan = plan_install(path, ctx.obj["TARGET"], [".mypy_cache"])
            debug_print_extracted_plan(plan)


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
