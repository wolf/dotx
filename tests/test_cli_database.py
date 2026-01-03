"""Tests for database-related CLI commands (list, verify, show, sync)."""
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from dotx.cli import app
from dotx.database import InstallationDB


def test_list_no_packages():
    """Test 'dotx list' with empty database."""
    with TemporaryDirectory() as db_dir:
        db_path = Path(db_dir) / "test.db"

        # Create empty database
        with InstallationDB(db_path):
            pass

        runner = CliRunner()
        # Note: We can't easily override the DB path via CLI, so this test
        # would need to mock the default DB location or we test the database directly
        # For now, let's test with the database module directly

        with InstallationDB(db_path) as db:
            packages = db.get_all_packages()
            assert packages == []


def test_list_with_packages(tmp_path):
    """Test 'dotx list' showing installed packages."""
    db_path = tmp_path / "test.db"
    package1 = tmp_path / "package1"
    package2 = tmp_path / "package2"
    package1.mkdir()
    package2.mkdir()

    # Create database with some installations
    with InstallationDB(db_path) as db:
        db.record_installation(package1, tmp_path / ".file1", "file")
        db.record_installation(package1, tmp_path / ".file2", "file")
        db.record_installation(package2, tmp_path / ".file3", "file")

    # Verify we can retrieve packages
    with InstallationDB(db_path) as db:
        packages = db.get_all_packages()
        assert len(packages) == 2

        # Find package1
        pkg1 = next(p for p in packages if Path(p["package_name"]).name == "package1")
        assert pkg1["file_count"] == 2

        # Find package2
        pkg2 = next(p for p in packages if Path(p["package_name"]).name == "package2")
        assert pkg2["file_count"] == 1


def test_verify_all_good(tmp_path):
    """Test 'dotx verify' when all installations are valid."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    source_file = package / "bashrc"
    source_file.write_text("# bashrc")

    target_file = tmp_path / ".bashrc"
    target_file.symlink_to(source_file)

    # Record installation
    with InstallationDB(db_path) as db:
        db.record_installation(package, target_file, "file")

    # Verify - should have no issues
    with InstallationDB(db_path) as db:
        issues = db.verify_installations(package)
        assert issues == []


def test_verify_missing_file(tmp_path):
    """Test 'dotx verify' detects missing files."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    target_file = tmp_path / ".bashrc"

    # Record installation but don't create the file
    with InstallationDB(db_path) as db:
        db.record_installation(package, target_file, "file")

    # Verify - should detect missing file
    with InstallationDB(db_path) as db:
        issues = db.verify_installations(package)
        assert len(issues) == 1
        assert "missing" in issues[0]["issue"].lower()
        assert str(target_file) == issues[0]["target_path"]


def test_verify_not_symlink(tmp_path):
    """Test 'dotx verify' detects files that should be symlinks but aren't."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    target_file = tmp_path / ".bashrc"
    target_file.write_text("# not a symlink")  # Regular file, not symlink

    # Record as if it were a symlink
    with InstallationDB(db_path) as db:
        db.record_installation(package, target_file, "file")

    # Verify - should detect it's not a symlink
    with InstallationDB(db_path) as db:
        issues = db.verify_installations(package)
        assert len(issues) == 1
        assert "not a symlink" in issues[0]["issue"].lower()


def test_show_package(tmp_path):
    """Test 'dotx show' displays package installation details."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    # Record multiple installations
    with InstallationDB(db_path) as db:
        db.record_installation(package, tmp_path / ".file1", "file")
        db.record_installation(package, tmp_path / ".file2", "file")
        db.record_installation(package, tmp_path / ".dir", "directory")

    # Get installations
    with InstallationDB(db_path) as db:
        installations = db.get_installations(package)
        assert len(installations) == 3

        # Check we have all three types
        types = {inst["link_type"] for inst in installations}
        assert "file" in types
        assert "directory" in types


def test_show_nonexistent_package(tmp_path):
    """Test 'dotx show' with package that doesn't exist in database."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "nonexistent"
    package.mkdir()

    with InstallationDB(db_path):
        pass  # Empty database

    with InstallationDB(db_path) as db:
        installations = db.get_installations(package)
        assert installations == []


def test_sync_database_operations(tmp_path):
    """Test database operations for sync command."""
    db_path = tmp_path / "test.db"

    # Create a source package and symlinks
    package = tmp_path / "source" / "package"
    package.mkdir(parents=True)

    source_file1 = package / "file1"
    source_file1.write_text("content1")
    source_file2 = package / "file2"
    source_file2.write_text("content2")

    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Create symlinks
    link1 = target_dir / "file1"
    link1.symlink_to(source_file1)
    link2 = target_dir / "file2"
    link2.symlink_to(source_file2)

    # Record in database
    with InstallationDB(db_path) as db:
        db.record_installation(package, link1, "file")
        db.record_installation(package, link2, "file")

    # Verify database has the records (should store symlink paths, not resolved paths)
    with InstallationDB(db_path) as db:
        installations = db.get_installations(package)
        assert len(installations) == 2
        assert str(link1.absolute()) in [inst["target_path"] for inst in installations]
        assert str(link2.absolute()) in [inst["target_path"] for inst in installations]


def test_orphaned_entries(tmp_path):
    """Test finding and cleaning orphaned database entries."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    target1 = tmp_path / ".exists"
    target2 = tmp_path / ".missing"

    # Create one file but not the other
    target1.touch()

    # Record both in database
    with InstallationDB(db_path) as db:
        db.record_installation(package, target1, "file")
        db.record_installation(package, target2, "file")

    # Find orphaned entries
    with InstallationDB(db_path) as db:
        orphaned = db.get_orphaned_entries(package)
        assert len(orphaned) == 1
        assert str(target2.absolute()) == orphaned[0]["target_path"]

    # Clean orphaned entries
    with InstallationDB(db_path) as db:
        removed_count = db.clean_orphaned_entries(package)
        assert removed_count == 1

    # Verify orphaned entry was removed
    with InstallationDB(db_path) as db:
        installations = db.get_installations(package)
        assert len(installations) == 1
        assert str(target1.absolute()) == installations[0]["target_path"]


def test_package_exists(tmp_path):
    """Test checking if package exists in database."""
    db_path = tmp_path / "test.db"
    package1 = tmp_path / "package1"
    package2 = tmp_path / "package2"
    package1.mkdir()
    package2.mkdir()

    # Record installation for package1 only
    with InstallationDB(db_path) as db:
        db.record_installation(package1, tmp_path / ".file", "file")

    # Check existence
    with InstallationDB(db_path) as db:
        assert db.package_exists(package1) is True
        assert db.package_exists(package2) is False


def test_cli_list_no_packages(tmp_path, monkeypatch):
    """Test 'dotx list' with no installed packages."""
    # Override XDG_CONFIG_HOME to use test directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    runner = CliRunner()
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No packages installed" in result.output


def test_cli_list_with_packages(tmp_path, monkeypatch):
    """Test 'dotx list' showing installed packages."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create source packages
    source1 = tmp_path / "source1"
    source1.mkdir()
    (source1 / "file1").write_text("content")

    source2 = tmp_path / "source2"
    source2.mkdir()
    (source2 / "file2").write_text("content")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()

    # Install both packages
    result = runner.invoke(app, [f"--target={target}", "install", str(source1)])
    assert result.exit_code == 0

    result = runner.invoke(app, [f"--target={target}", "install", str(source2)])
    assert result.exit_code == 0

    # List packages
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "source1" in result.output
    assert "source2" in result.output
    assert "Total: 2 package(s)" in result.output


def test_cli_list_as_commands(tmp_path, monkeypatch):
    """Test 'dotx list --as-commands' output."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # List as commands
    result = runner.invoke(app, ["list", "--as-commands"])

    assert result.exit_code == 0
    assert "dotx install" in result.output
    assert str(source) in result.output


def test_cli_verify_all_packages(tmp_path, monkeypatch):
    """Test 'dotx verify' for all packages."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()

    # Install the package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Verify all packages - should pass
    result = runner.invoke(app, ["verify"])

    assert result.exit_code == 0
    assert "verified successfully" in result.output.lower()


def test_cli_verify_specific_package(tmp_path, monkeypatch):
    """Test 'dotx verify' for a specific package."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Verify specific package
    result = runner.invoke(app, ["verify", str(source)])

    assert result.exit_code == 0
    assert "verified successfully" in result.output.lower()


def test_cli_verify_detects_missing_file(tmp_path, monkeypatch):
    """Test 'dotx verify' detects when installed file is missing."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Delete the installed file
    installed_file = target / "file1"
    installed_file.unlink()

    # Verify should detect missing file
    result = runner.invoke(app, ["verify", str(source)])

    assert result.exit_code == 0
    assert "issue" in result.output.lower() or "missing" in result.output.lower()


def test_cli_show_package(tmp_path, monkeypatch):
    """Test 'dotx show' displays package installation details."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create and install a package with multiple files
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content1")
    (source / "file2").write_text("content2")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Show package details
    result = runner.invoke(app, ["show", str(source)])

    assert result.exit_code == 0
    assert "Package:" in result.output
    assert "Installed files: 2" in result.output
    assert str(target / "file1") in result.output
    assert str(target / "file2") in result.output


def test_cli_show_nonexistent_package(tmp_path, monkeypatch):
    """Test 'dotx show' with package not in database."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create package but don't install it
    source = tmp_path / "source"
    source.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, ["show", str(source)])

    assert result.exit_code == 0
    assert "No installations found" in result.output


def test_cli_sync_dry_run(tmp_path, monkeypatch):
    """Test 'dotx sync --dry-run' previews changes without modifying database."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    # Create source and symlinks
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "bashrc"
    source_file.write_text("# bashrc")

    target = tmp_path / "target"
    target.mkdir()
    link = target / ".bashrc"
    link.symlink_to(source_file)

    runner = CliRunner()
    result = runner.invoke(app, [f"--target={target}", "sync", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "no database changes" in result.output.lower()


def test_cli_sync_no_symlinks(tmp_path, monkeypatch):
    """Test 'dotx sync' when no symlinks exist."""
    # Override XDG_CONFIG_HOME
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

    target = tmp_path / "target"
    target.mkdir()

    # Create a regular file (not a symlink)
    (target / "regular_file").write_text("content")

    runner = CliRunner()
    result = runner.invoke(app, [f"--target={target}", "sync"])

    assert result.exit_code == 0
    assert "No symlinks found" in result.output


def test_database_schema_version(tmp_path):
    """Test that database schema version is tracked correctly."""
    db_path = tmp_path / "test.db"

    # Create database
    with InstallationDB(db_path) as db:
        # Check schema version in metadata
        assert db.conn is not None
        cursor = db.conn.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        )
        version_row = cursor.fetchone()
        assert version_row is not None
        assert version_row["value"] == "2"
