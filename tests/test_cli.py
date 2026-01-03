from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from typer.testing import CliRunner

from dotx.cli import app


def test_install_normal_file():
    with TemporaryDirectory() as source_package_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path("SIMPLE-FILE")
        (source_package_root_path / file_path).touch()

        runner = CliRunner()
        result = runner.invoke(app, ["--dry-run", "install", source_package_root])

        print()
        print(result.output)

        assert "can't install" not in result.output


@pytest.mark.skip("Typer testing - needs investigation.")
def test_options_functions():
    runner = CliRunner()
    result = runner.invoke(app, ["--verbose", "--debug", "--dry-run", "debug"])

    assert len(result.output) == 0
