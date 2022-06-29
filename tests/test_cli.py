from pathlib import Path
from tempfile import TemporaryDirectory

from click.testing import CliRunner
import pytest


from cli import cli


def test_install_normal_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path("SIMPLE-FILE")
        (source_package_root_path / file_path).touch()

        runner = CliRunner()
        result = runner.invoke(cli, f"--target={destination_root} install {source_package_root}")

        assert "can't install" not in result.output


@pytest.mark.skip("Click isn't doing the right thing here.")
def test_options_functions():
    runner = CliRunner
    result = runner.invoke(cli, "--verbose --debug --dry-run debug")

    assert len(result.output) == 0
