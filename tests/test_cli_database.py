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
        db.record_installation(tmp_path, "package1", package1, tmp_path / ".file1", "file")
        db.record_installation(tmp_path, "package1", package1, tmp_path / ".file2", "file")
        db.record_installation(tmp_path, "package2", package2, tmp_path / ".file3", "file")

    # Verify we can retrieve packages
    with InstallationDB(db_path) as db:
        packages = db.get_all_packages()
        assert len(packages) == 2

        # Find package1
        pkg1 = next(p for p in packages if p["package_name"] == "package1")
        assert pkg1["file_count"] == 2

        # Find package2
        pkg2 = next(p for p in packages if p["package_name"] == "package2")
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
        db.record_installation(tmp_path, "package", package, target_file, "file")

    # Verify - should have no issues
    with InstallationDB(db_path) as db:
        issues = db.verify_installations(tmp_path, "package")
        assert issues == []


def test_verify_missing_file(tmp_path):
    """Test 'dotx verify' detects missing files."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    target_file = tmp_path / ".bashrc"

    # Record installation but don't create the file
    with InstallationDB(db_path) as db:
        db.record_installation(tmp_path, "package", package, target_file, "file")

    # Verify - should detect missing file
    with InstallationDB(db_path) as db:
        issues = db.verify_installations(tmp_path, "package")
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
        db.record_installation(tmp_path, "package", package, target_file, "file")

    # Verify - should detect it's not a symlink
    with InstallationDB(db_path) as db:
        issues = db.verify_installations(tmp_path, "package")
        assert len(issues) == 1
        assert "not a symlink" in issues[0]["issue"].lower()


def test_show_package(tmp_path):
    """Test 'dotx show' displays package installation details."""
    db_path = tmp_path / "test.db"
    package = tmp_path / "package"
    package.mkdir()

    # Record multiple installations
    with InstallationDB(db_path) as db:
        db.record_installation(tmp_path, "package", package, tmp_path / ".file1", "file")
        db.record_installation(tmp_path, "package", package, tmp_path / ".file2", "file")
        db.record_installation(tmp_path, "package", package, tmp_path / ".dir", "directory")

    # Get installations
    with InstallationDB(db_path) as db:
        installations = db.get_installations(tmp_path, "package")
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
        installations = db.get_installations(tmp_path, "nonexistent")
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
    package_root = package.parent
    package_name = package.name
    with InstallationDB(db_path) as db:
        db.record_installation(package_root, package_name, package, link1, "file")
        db.record_installation(package_root, package_name, package, link2, "file")

    # Verify database has the records (should store symlink paths, not resolved paths)
    with InstallationDB(db_path) as db:
        installations = db.get_installations(package_root, package_name)
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
        db.record_installation(tmp_path, "package", package, target1, "file")
        db.record_installation(tmp_path, "package", package, target2, "file")

    # Find orphaned entries
    with InstallationDB(db_path) as db:
        orphaned = db.get_orphaned_entries(tmp_path, "package")
        assert len(orphaned) == 1
        assert str(target2.absolute()) == orphaned[0]["target_path"]

    # Clean orphaned entries
    with InstallationDB(db_path) as db:
        removed_count = db.clean_orphaned_entries(tmp_path, "package")
        assert removed_count == 1

    # Verify orphaned entry was removed
    with InstallationDB(db_path) as db:
        installations = db.get_installations(tmp_path, "package")
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
        db.record_installation(tmp_path, "package1", package1, tmp_path / ".file", "file")

    # Check existence
    with InstallationDB(db_path) as db:
        assert db.package_exists(tmp_path, "package1") is True
        assert db.package_exists(tmp_path, "package2") is False


def test_cli_list_no_packages(tmp_path, monkeypatch):
    """Test 'dotx list' with no installed packages."""
    # Override XDG_DATA_HOME to use test directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    runner = CliRunner()
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No packages installed" in result.output


def test_cli_list_with_packages(tmp_path, monkeypatch):
    """Test 'dotx list' showing installed packages."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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

    # List packages (use --as-commands for reliable testing)
    result = runner.invoke(app, ["list", "--as-commands"])

    assert result.exit_code == 0
    assert f"dotx install {source1}" in result.output
    assert f"dotx install {source2}" in result.output

    # Also verify table format shows count
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Total: 2 package(s)" in result.output


def test_cli_list_as_commands(tmp_path, monkeypatch):
    """Test 'dotx list --as-commands' output."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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
    # Rich may wrap long paths, so just check for the filenames
    assert "file1" in result.output
    assert "file2" in result.output


def test_cli_show_nonexistent_package(tmp_path, monkeypatch):
    """Test 'dotx show' with package not in database."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create package but don't install it
    source = tmp_path / "source"
    source.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, ["show", str(source)])

    assert result.exit_code == 0
    assert "No installations found" in result.output


def test_cli_sync_dry_run(tmp_path, monkeypatch):
    """Test 'dotx sync --dry-run' previews changes without modifying database."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "config"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

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


def test_cli_sync_clean_dry_run(tmp_path, monkeypatch):
    """Test 'dotx sync --clean --dry-run' shows what would be cleaned."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content1")
    (source / "file2").write_text("content2")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()

    # Install package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Verify both files are installed
    assert (target / "file1").exists()
    assert (target / "file2").exists()

    # Delete one symlink manually (simulating orphaned entry)
    (target / "file1").unlink()

    # Sync --clean --dry-run should show what would be cleaned
    result = runner.invoke(
        app, [f"--target={target}", "sync", "--dry-run", "--clean", "--package-root", str(source.parent)]
    )

    assert result.exit_code == 0
    assert "Would clean orphaned entries" in result.output
    assert "Would remove 1 orphaned entry(ies)" in result.output
    assert "Dry run" in result.output


def test_cli_sync_clean(tmp_path, monkeypatch):
    """Test 'dotx sync --clean' removes orphaned database entries."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content1")
    (source / "file2").write_text("content2")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()

    # Install package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Verify both files are installed
    assert (target / "file1").exists()
    assert (target / "file2").exists()

    # Check database has 2 entries
    with InstallationDB() as db:
        installations = db.get_installations(source.parent, source.name)
        assert len(installations) == 2

    # Delete one symlink manually (simulating orphaned entry)
    (target / "file1").unlink()

    # Sync --clean should remove the orphaned entry
    result = runner.invoke(
        app,
        [f"--target={target}", "sync", "--clean", "--package-root", str(source.parent)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Cleaning orphaned entries" in result.output
    assert "Removed 1 orphaned entry(ies)" in result.output

    # Check database now has only 1 entry
    with InstallationDB() as db:
        installations = db.get_installations(source.parent, source.name)
        assert len(installations) == 1
        # The remaining entry should be for file2
        assert installations[0]["target_path"] == str((target / "file2").absolute())


def test_cli_sync_clean_no_orphans(tmp_path, monkeypatch):
    """Test 'dotx sync --clean' when there are no orphaned entries."""
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create and install a package
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1").write_text("content1")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()

    # Install package
    result = runner.invoke(app, [f"--target={target}", "install", str(source)])
    assert result.exit_code == 0

    # Sync --clean with no orphaned entries
    result = runner.invoke(
        app,
        [f"--target={target}", "sync", "--clean", "--package-root", str(source.parent)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Cleaning orphaned entries" in result.output
    assert "No orphaned entries found" in result.output


def test_package_name_semantic_not_implementation(tmp_path):
    """Test that package names are semantic (e.g., 'helix') not implementation details (e.g., 'dot-config')."""
    db_path = tmp_path / "test.db"

    # Create a package structure: dotfiles/helix/dot-config/settings.toml
    dotfiles = tmp_path / "dotfiles"
    helix_pkg = dotfiles / "helix"
    dot_config = helix_pkg / "dot-config"
    dot_config.mkdir(parents=True)

    (dot_config / "settings.toml").write_text("theme = 'dark'")

    # Record installation (simulating what install would do)
    with InstallationDB(db_path) as db:
        # Package root is dotfiles, package name is helix
        db.record_installation(
            dotfiles,
            "helix",
            dot_config,  # Source is the dot-config subdirectory
            tmp_path / ".config" / "helix" / "settings.toml",
            "file",
        )

    # Verify package name in get_all_packages
    with InstallationDB(db_path) as db:
        packages = db.get_all_packages()
        assert len(packages) == 1
        # Should show semantic name "helix", not "dot-config"
        assert packages[0]["package_name"] == "helix"
        # Package root should be dotfiles
        assert packages[0]["package_root"] == str(dotfiles.resolve())


def test_package_grouping_multiple_source_dirs(tmp_path):
    """Test that files from multiple source directories are grouped as one package."""
    db_path = tmp_path / "test.db"

    # Create package: dotfiles/shells with top-level files and subdirectory
    dotfiles = tmp_path / "dotfiles"
    shells_pkg = dotfiles / "shells"
    shells_config = shells_pkg / "dot-config"
    shells_config.mkdir(parents=True)

    (shells_pkg / "bashrc").touch()
    (shells_pkg / "zshrc").touch()
    (shells_config / "fish" / "config.fish").parent.mkdir(parents=True)
    (shells_config / "fish" / "config.fish").touch()

    # Record installations from different source directories
    with InstallationDB(db_path) as db:
        # Top-level files
        db.record_installation(dotfiles, "shells", shells_pkg, tmp_path / ".bashrc", "file")
        db.record_installation(dotfiles, "shells", shells_pkg, tmp_path / ".zshrc", "file")

        # Files from subdirectory
        db.record_installation(
            dotfiles,
            "shells",
            shells_config,  # Different source_package_root
            tmp_path / ".config" / "fish" / "config.fish",
            "file",
        )

    # Verify all files appear as ONE package
    with InstallationDB(db_path) as db:
        packages = db.get_all_packages()
        assert len(packages) == 1, "All files from 'shells' should be grouped together"

        pkg = packages[0]
        assert pkg["package_name"] == "shells"
        assert pkg["file_count"] == 3  # Should count all 3 files together


def test_v1_schema_detection(tmp_path):
    """Test that v1 database schema is detected and rejected with helpful error."""
    import sqlite3

    db_path = tmp_path / "test.db"

    # Create a v1 database schema (old format without package_root, package_name, source_package_root)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE installations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            target_path TEXT NOT NULL UNIQUE,
            link_type TEXT NOT NULL,
            installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_package_name ON installations(package_name);

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        INSERT INTO metadata (key, value) VALUES ('schema_version', '1');
    """)
    conn.commit()
    conn.close()

    # Try to open with InstallationDB - should raise RuntimeError with upgrade instructions
    try:
        with InstallationDB(db_path) as db:
            pass
        assert False, "Should have raised RuntimeError for v1 schema"
    except RuntimeError as e:
        error_msg = str(e)
        # Verify error message contains key information
        assert "Incompatible database schema detected" in error_msg
        assert "dotx sync --package-root" in error_msg
        assert str(db_path) in error_msg
        assert "rm" in error_msg  # Should tell user to delete old DB


def test_list_shows_correct_package_names_after_install(tmp_path, monkeypatch):
    """Test that 'dotx list' shows semantic package names, not implementation details.

    This is a regression test for the bug where dotx list showed 'dot-config'
    instead of actual package names like 'bash' or 'helix'.
    """
    # Override XDG_DATA_HOME
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))

    # Create a dotfiles structure with subdirectories (like real packages)
    dotfiles = tmp_path / "dotfiles"
    dotfiles.mkdir()

    # Package 1: bash with simple structure
    bash = dotfiles / "bash"
    bash.mkdir()
    (bash / "dot-bashrc").write_text("# bashrc")
    (bash / "dot-bash_profile").write_text("# bash_profile")

    # Package 2: helix with nested structure (dot-config subdirectory)
    helix = dotfiles / "helix"
    helix.mkdir()
    helix_config = helix / "dot-config" / "helix"
    helix_config.mkdir(parents=True)
    (helix_config / "config.toml").write_text("# helix config")
    (helix_config / "languages.toml").write_text("# helix languages")

    # Target directory
    target = tmp_path / "home"
    target.mkdir()

    runner = CliRunner()

    # Install both packages
    result = runner.invoke(app, [f"--target={target}", "install", str(bash)])
    assert result.exit_code == 0, f"bash install failed: {result.output}"

    result = runner.invoke(app, [f"--target={target}", "install", str(helix)])
    assert result.exit_code == 0, f"helix install failed: {result.output}"

    # Test --as-commands format (plain text, easy to verify)
    result = runner.invoke(app, ["list", "--as-commands"])
    assert result.exit_code == 0, f"list --as-commands failed: {result.output}"

    # Should output install commands with correct package paths
    assert f"dotx install {bash}" in result.output, f"Expected 'dotx install {bash}', got: {result.output}"
    assert f"dotx install {helix}" in result.output, f"Expected 'dotx install {helix}', got: {result.output}"

    # Should NOT show implementation details like 'dot-config'
    assert "dot-config" not in result.output, f"Should not show 'dot-config' in output, got: {result.output}"

    # Also verify the table format shows package names (even if truncated)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, f"list failed: {result.output}"
    assert "2 package(s)" in result.output  # Should show 2 packages
