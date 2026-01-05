"""Tests for path and which commands."""

from typer.testing import CliRunner

from dotx.cli import app
from dotx.database import InstallationDB


def test_path_command_found(tmp_path, monkeypatch):
    """Test 'dotx path' with an installed package."""
    # Override XDG_DATA_HOME to use test directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create package structure
    package_root = tmp_path / "dotfiles"
    package_root.mkdir()
    package_dir = package_root / "bash"
    package_dir.mkdir()
    (package_dir / "bashrc").write_text("test")

    # Record installation in database
    with InstallationDB() as db:
        db.record_installation(
            package_root=package_root,
            package_name="bash",
            source_package_root=package_dir,
            target_path=tmp_path / ".bashrc",
            link_type="file",
        )

    runner = CliRunner()
    result = runner.invoke(app, ["path", "bash"])

    assert result.exit_code == 0
    assert str(package_dir.resolve()) in result.output.strip()


def test_path_command_not_found(tmp_path, monkeypatch):
    """Test 'dotx path' with a package that doesn't exist."""
    # Override XDG_DATA_HOME to use test directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    runner = CliRunner()
    result = runner.invoke(app, ["path", "nonexistent"])

    assert result.exit_code == 1


def test_path_command_multiple_source_roots(tmp_path, monkeypatch):
    """Test 'dotx path' with package that has files from multiple source directories."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create package with multiple source directories (like shells example)
    package_root = tmp_path / "dotfiles"
    package_root.mkdir()

    shells_main = package_root / "shells"
    shells_main.mkdir()
    shells_config = shells_main / "dot-config"
    shells_config.mkdir()

    # Record installations from both directories
    with InstallationDB() as db:
        db.record_installation(
            package_root=package_root,
            package_name="shells",
            source_package_root=shells_main,
            target_path=tmp_path / ".bashrc",
            link_type="file",
        )
        db.record_installation(
            package_root=package_root,
            package_name="shells",
            source_package_root=shells_config,
            target_path=tmp_path / ".config" / "fish" / "config.fish",
            link_type="file",
        )

    runner = CliRunner()
    result = runner.invoke(app, ["path", "shells"])

    assert result.exit_code == 0
    output_lines = result.output.strip().split("\n")
    # Should print both source roots, sorted
    assert len(output_lines) == 2
    assert str(shells_config.resolve()) in output_lines
    assert str(shells_main.resolve()) in output_lines


def test_path_command_with_package_root_filter(tmp_path, monkeypatch):
    """Test 'dotx path' with --package-root to disambiguate."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create two different package roots with same package name
    root1 = tmp_path / "dotfiles1"
    root1.mkdir()
    bash1 = root1 / "bash"
    bash1.mkdir()

    root2 = tmp_path / "dotfiles2"
    root2.mkdir()
    bash2 = root2 / "bash"
    bash2.mkdir()

    # Record both in database
    with InstallationDB() as db:
        db.record_installation(
            package_root=root1,
            package_name="bash",
            source_package_root=bash1,
            target_path=tmp_path / ".bashrc",
            link_type="file",
        )
        db.record_installation(
            package_root=root2,
            package_name="bash",
            source_package_root=bash2,
            target_path=tmp_path / ".bashrc2",
            link_type="file",
        )

    runner = CliRunner()

    # Query for bash in root1
    result = runner.invoke(app, ["path", "bash", "--package-root", str(root1)])
    assert result.exit_code == 0
    assert str(bash1.resolve()) in result.output
    assert str(bash2.resolve()) not in result.output

    # Query for bash in root2
    result = runner.invoke(app, ["path", "bash", "--package-root", str(root2)])
    assert result.exit_code == 0
    assert str(bash2.resolve()) in result.output
    assert str(bash1.resolve()) not in result.output


def test_which_command_found(tmp_path, monkeypatch):
    """Test 'dotx which' with a file that exists in database."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create package structure
    package_root = tmp_path / "dotfiles"
    package_root.mkdir()
    package_dir = package_root / "bash"
    package_dir.mkdir()

    target_file = tmp_path / ".bashrc"

    # Record installation
    with InstallationDB() as db:
        db.record_installation(
            package_root=package_root,
            package_name="bash",
            source_package_root=package_dir,
            target_path=target_file,
            link_type="file",
        )

    runner = CliRunner()
    result = runner.invoke(app, ["which", str(target_file)])

    assert result.exit_code == 0
    assert result.output.strip() == "bash"


def test_which_command_not_found(tmp_path, monkeypatch):
    """Test 'dotx which' with a file that doesn't exist in database."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    runner = CliRunner()
    result = runner.invoke(app, ["which", str(tmp_path / ".nonexistent")])

    assert result.exit_code == 1


def test_which_command_composition(tmp_path, monkeypatch):
    """Test composing 'dotx which' with 'dotx path'."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create package structure
    package_root = tmp_path / "dotfiles"
    package_root.mkdir()
    vim_dir = package_root / "vim"
    vim_dir.mkdir()

    target_file = tmp_path / ".vimrc"

    # Record installation
    with InstallationDB() as db:
        db.record_installation(
            package_root=package_root,
            package_name="vim",
            source_package_root=vim_dir,
            target_path=target_file,
            link_type="file",
        )

    runner = CliRunner()

    # Get package name
    which_result = runner.invoke(app, ["which", str(target_file)])
    assert which_result.exit_code == 0
    package_name = which_result.output.strip()
    assert package_name == "vim"

    # Use that to get path
    path_result = runner.invoke(app, ["path", package_name])
    assert path_result.exit_code == 0
    assert str(vim_dir.resolve()) in path_result.output
