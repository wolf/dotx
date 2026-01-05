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


def test_cli_install_conflict_detection(tmp_path):
    """Test install detects and reports conflicts with existing files."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source file
    (source / "file1").write_text("source content")

    # Create conflicting file in target (not a symlink)
    (target / "file1").write_text("existing content")

    runner = CliRunner()

    # Try to install - should fail with conflict
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])

    assert result.exit_code == 0  # CLI doesn't return error code, just refuses
    assert "can't install" in result.output.lower()
    assert "would overwrite" in result.output.lower()
    assert "Refusing to install" in result.output
    assert "conflicts detected" in result.output


def test_cli_install_with_verbose(tmp_path, isolated_db):
    """Test install with --verbose flag shows individual files."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source files
    (source / "file1").write_text("content1")
    (source / "file2").write_text("content2")

    runner = CliRunner()

    # Install with --verbose
    result = runner.invoke(app, [f"--target={target}", "--verbose", "install", str(source)])

    assert result.exit_code == 0
    assert "file1" in result.output
    assert "file2" in result.output
    assert f"Installing {source.name}" in result.output


def test_cli_install_multiple_packages(tmp_path, isolated_db):
    """Test installing multiple packages in one command."""
    source1 = tmp_path / "source1"
    source2 = tmp_path / "source2"
    source1.mkdir()
    source2.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source files
    (source1 / "file1").write_text("content1")
    (source2 / "file2").write_text("content2")

    runner = CliRunner()

    # Install both packages
    result = runner.invoke(app, [f"--target={target}", "install", str(source1), str(source2)])

    assert result.exit_code == 0
    assert "2 file(s)" in result.output
    assert "2 package(s)" in result.output
    assert (target / "file1").exists()
    assert (target / "file2").exists()


def test_cli_uninstall_basic(tmp_path, isolated_db):
    """Test basic uninstall command via CLI."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source files
    (source / "file1").write_text("content1")
    (source / "file2").write_text("content2")

    runner = CliRunner()

    # Install the package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Verify files are installed
    assert (target / "file1").exists()
    assert (target / "file2").exists()

    # Uninstall the package
    result = runner.invoke(app, [f"--target={target}", "uninstall", str(source)])

    assert result.exit_code == 0
    assert "Removed 2 symlink(s)" in result.output
    assert not (target / "file1").exists()
    assert not (target / "file2").exists()


def test_cli_uninstall_multiple_packages(tmp_path, isolated_db):
    """Test uninstalling multiple packages in one command."""
    source1 = tmp_path / "source1"
    source2 = tmp_path / "source2"
    source1.mkdir()
    source2.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source files
    (source1 / "file1").write_text("content1")
    (source2 / "file2").write_text("content2")

    runner = CliRunner()

    # Install both packages
    result = runner.invoke(app, [f"--target={target}", "install", str(source1)])
    assert result.exit_code == 0
    result = runner.invoke(app, [f"--target={target}", "install", str(source2)])
    assert result.exit_code == 0

    # Verify files are installed
    assert (target / "file1").exists()
    assert (target / "file2").exists()

    # Uninstall both packages
    result = runner.invoke(app, [f"--target={target}", "uninstall", str(source1), str(source2)])

    assert result.exit_code == 0
    assert "Removed 2 symlink(s)" in result.output
    assert "2 package(s)" in result.output
    assert not (target / "file1").exists()
    assert not (target / "file2").exists()


def test_cli_uninstall_with_verbose(tmp_path, isolated_db):
    """Test uninstall with --verbose flag shows individual files."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source files
    (source / "file1").write_text("content1")
    (source / "file2").write_text("content2")

    runner = CliRunner()

    # Install the package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Uninstall with --verbose
    result = runner.invoke(app, [f"--target={target}", "--verbose", "uninstall", str(source)])

    assert result.exit_code == 0
    assert "file1" in result.output
    assert "file2" in result.output
    assert f"Uninstalling {source.name}" in result.output


def test_cli_uninstall_dry_run(tmp_path, isolated_db):
    """Test uninstall with --dry-run doesn't actually remove files."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create source files
    (source / "file1").write_text("content1")

    runner = CliRunner()

    # Install the package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0
    assert (target / "file1").exists()

    # Uninstall with --dry-run
    result = runner.invoke(app, [f"--target={target}", "--dry-run", "uninstall", str(source)])

    assert result.exit_code == 0
    # File should still exist after dry-run
    assert (target / "file1").exists()


def test_cli_uninstall_with_directories(tmp_path, isolated_db):
    """Test uninstall handles directory symlinks correctly."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()

    # Create a nested directory structure
    config_dir = source / "config"
    config_dir.mkdir()
    (config_dir / "settings.conf").write_text("settings")

    runner = CliRunner()

    # Install the package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Verify directory is installed
    assert (target / "config").exists()
    assert (target / "config").is_symlink()

    # Uninstall the package
    result = runner.invoke(app, [f"--target={target}", "uninstall", str(source)])

    assert result.exit_code == 0
    assert "1 symlink(s)" in result.output
    assert not (target / "config").exists()


@pytest.mark.skip("Typer testing - needs investigation.")
def test_options_functions():
    runner = CliRunner()
    result = runner.invoke(app, ["--verbose", "--debug", "--dry-run", "debug"])

    assert len(result.output) == 0
