"""Path and which commands for dotx CLI - query installed packages."""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from dotx.database import InstallationDB


def register_commands(app: typer.Typer):
    """Register the path command with the Typer app."""

    @app.command()
    def path(
        package: Annotated[
            str,
            typer.Argument(help="Package name to get path for"),
        ],
        package_root: Annotated[
            Path | None,
            typer.Option(help="Package root to disambiguate (if package exists in multiple roots)"),
        ] = None,
    ):
        """
        Print the source path of an installed package.

        Prints the path(s) where the package files are located, one per line.
        Useful for composition with other tools: tree $(dotx path bash)

        Exit codes:
          0 - Package found, path(s) printed
          1 - Package not found
        """
        logger.info(f"path command for package: {package}")

        with InstallationDB() as db:
            # Get all packages
            all_packages = db.get_all_packages()

            # Filter by package name
            matching = [
                pkg
                for pkg in all_packages
                if pkg["package_name"] == package
                and (package_root is None or Path(pkg["package_root"]).resolve() == package_root.resolve())
            ]

            if not matching:
                if package_root:
                    logger.error(f"Package '{package}' not found in package_root {package_root}")
                else:
                    logger.error(f"Package '{package}' not found")
                raise typer.Exit(code=1)

            # For each matching package, get unique source paths
            for pkg in matching:
                # Get installations for this package to find source paths
                installations = db.get_installations(Path(pkg["package_root"]), pkg["package_name"])

                # Collect unique source_package_root values
                source_roots = sorted(set(install["source_package_root"] for install in installations))

                # Print each unique source root
                for source_root in source_roots:
                    typer.echo(source_root)

        logger.info("path command finished")

    @app.command()
    def which(
        target_file: Annotated[
            Path,
            typer.Argument(help="Target file to find package for"),
        ],
    ):
        """
        Print the package name that owns a target file.

        Simple output for composition: dotx path $(dotx which ~/.bashrc)

        Exit codes:
          0 - File found, package name printed
          1 - File not found in database
        """
        logger.info(f"which command for file: {target_file}")

        # Make path absolute for database lookup
        target_abs = target_file.absolute()

        with InstallationDB() as db:
            # Query database for this target path
            # We need to search through all installations to find matching target_path
            all_packages = db.get_all_packages()

            for pkg in all_packages:
                installations = db.get_installations(Path(pkg["package_root"]), pkg["package_name"])
                for install in installations:
                    if Path(install["target_path"]) == target_abs:
                        # Found it - print package name and exit
                        typer.echo(pkg["package_name"])
                        logger.info("which command finished")
                        return

            # Not found
            logger.error(f"File '{target_file}' not managed by any package")
            raise typer.Exit(code=1)
