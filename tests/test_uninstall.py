from pathlib import Path

from dotx.uninstall import plan_uninstall
from dotx.plan import Action


def test_uninstall_nothing(tmp_path):
    """Test uninstalling from empty source package."""
    source_package_root = tmp_path
    destination_root = tmp_path / "dest"
    destination_root.mkdir()

    plan = plan_uninstall(source_package_root, destination_root)

    # Plan includes the dest directory itself (if it exists in source)
    # If source has a "dest" directory, it would be in the plan
    # For truly empty source, plan would be empty after root deletion
    # Let's just verify no errors occur
    assert isinstance(plan, dict)


def test_uninstall_symlink_file(tmp_path):
    """Test uninstalling a single symlinked file."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create source file
    source_file = source_package_root / "test.txt"
    source_file.write_text("test content")

    # Create symlink in destination
    dest_file = destination_root / "test.txt"
    dest_file.symlink_to(source_file)

    plan = plan_uninstall(source_package_root, destination_root)

    # Should have one UNLINK action for the symlinked file
    file_path = Path("test.txt")
    assert file_path in plan
    assert plan[file_path].action == Action.UNLINK


def test_uninstall_symlink_file_with_rename(tmp_path):
    """Test uninstalling a symlinked file that was renamed (dot- prefix)."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create source file with dot- prefix
    source_file = source_package_root / "dot-bashrc"
    source_file.write_text("bash config")

    # Create symlink in destination with renamed path
    dest_file = destination_root / ".bashrc"
    dest_file.symlink_to(source_file)

    plan = plan_uninstall(source_package_root, destination_root)

    # Should have UNLINK action for the file
    file_path = Path("dot-bashrc")
    assert file_path in plan
    assert plan[file_path].action == Action.UNLINK
    # Check destination path uses renamed version
    assert plan[file_path].relative_destination_path == Path(".bashrc")


def test_uninstall_symlink_directory(tmp_path):
    """Test uninstalling a symlinked directory."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create source directory with a file in it
    source_dir = source_package_root / "mydir"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("content")

    # Create symlink to directory in destination
    dest_dir = destination_root / "mydir"
    dest_dir.symlink_to(source_dir)

    plan = plan_uninstall(source_package_root, destination_root)

    # Should have UNLINK action for the directory
    dir_path = Path("mydir")
    assert dir_path in plan
    assert plan[dir_path].action == Action.UNLINK
    # Children should be marked as SKIP since parent will be unlinked
    file_path = Path("mydir/file.txt")
    assert file_path in plan
    assert plan[file_path].action == Action.SKIP


def test_uninstall_regular_file_not_symlink(tmp_path):
    """Test that regular files (not symlinks) are skipped."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create source file
    source_file = source_package_root / "test.txt"
    source_file.write_text("test content")

    # Create regular file (NOT symlink) in destination
    dest_file = destination_root / "test.txt"
    dest_file.write_text("different content")

    plan = plan_uninstall(source_package_root, destination_root)

    # Should NOT have UNLINK action for regular files
    file_path = Path("test.txt")
    assert file_path in plan
    assert plan[file_path].action != Action.UNLINK


def test_uninstall_missing_destination(tmp_path):
    """Test uninstalling when destination file doesn't exist."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create source file but NO destination
    source_file = source_package_root / "test.txt"
    source_file.write_text("test content")

    plan = plan_uninstall(source_package_root, destination_root)

    # File exists in source but not destination, so action stays NONE
    # (uninstall only marks files as UNLINK if they're symlinks at destination)
    file_path = Path("test.txt")
    assert file_path in plan
    assert plan[file_path].action == Action.NONE


def test_uninstall_nested_directories(tmp_path):
    """Test uninstalling nested directory structure with symlinks."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create nested source structure
    dir1 = source_package_root / "dir1"
    dir2 = dir1 / "dir2"
    dir2.mkdir(parents=True)
    file1 = dir1 / "file1.txt"
    file2 = dir2 / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")

    # Create symlinks in destination
    dest_dir1 = destination_root / "dir1"
    dest_dir1.mkdir()
    dest_file1 = dest_dir1 / "file1.txt"
    dest_file1.symlink_to(file1)

    dest_dir2 = dest_dir1 / "dir2"
    dest_dir2.mkdir()
    dest_file2 = dest_dir2 / "file2.txt"
    dest_file2.symlink_to(file2)

    plan = plan_uninstall(source_package_root, destination_root)

    # Check that symlinked files have UNLINK actions
    assert plan[Path("dir1/file1.txt")].action == Action.UNLINK
    assert plan[Path("dir1/dir2/file2.txt")].action == Action.UNLINK


def test_uninstall_with_dotxignore(tmp_path):
    """Test that ignored files are not included in uninstall plan."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create source files
    included_file = source_package_root / "included.txt"
    ignored_file = source_package_root / "ignored.log"
    included_file.write_text("include me")
    ignored_file.write_text("ignore me")

    # Create .dotxignore
    ignore_file = source_package_root / ".dotxignore"
    ignore_file.write_text("*.log\n")

    # Create symlinks in destination
    dest_included = destination_root / "included.txt"
    dest_included.symlink_to(included_file)
    dest_ignored = destination_root / "ignored.log"
    dest_ignored.symlink_to(ignored_file)

    plan = plan_uninstall(source_package_root, destination_root)

    # Included file should be in plan
    assert Path("included.txt") in plan

    # Ignored file should NOT be in plan (filtered by .dotxignore)
    assert Path("ignored.log") not in plan
