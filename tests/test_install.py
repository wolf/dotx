from pathlib import Path

from dotx.install import plan_install, plan_install_paths
from dotx.plan import Action, PlanNode


def test_plan_paths_nothing(tmp_path):
    source_package_root = tmp_path

    plan = plan_install_paths(source_package_root)

    assert len(plan) == 1


def test_plan_paths_normal_file(tmp_path):
    source_package_root_path = tmp_path
    file_path = Path("SIMPLE-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 2
    assert plan[file_path] == PlanNode(
        Action.NONE, False, file_path, file_path, False
    )


def test_plan_paths_normal_file_fail(tmp_path):
    source_package_root_path = tmp_path
    file_path = Path("SIMPLE-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 2
    assert plan[file_path] == PlanNode(
        Action.NONE, False, file_path, file_path, False
    )


def test_plan_paths_hidden_file(tmp_path):
    source_package_root_path = tmp_path
    file_path = Path(".HIDDEN-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 2
    assert plan[file_path] == PlanNode(
        Action.NONE, False, file_path, file_path, False
    )


def test_plan_paths_file_with_renaming(tmp_path):
    source_package_root_path = tmp_path
    file_path = Path("dot-SIMPLE-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 2
    assert plan[file_path] == PlanNode(
        Action.NONE, True, file_path, Path(".SIMPLE-FILE"), False
    )


def test_plan_paths_dir(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path("SIMPLE-DIR")
    file_path = dir_path / "SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 3
    assert plan[dir_path] == PlanNode(Action.NONE, False, dir_path, dir_path, True)
    assert plan[file_path].action == Action.NONE


def test_plan_paths_dir_inside_dir(tmp_path):
    source_package_root_path = tmp_path
    dir1_path = Path("SIMPLE-DIR1")
    dir2_path = dir1_path / "SIMPLE-DIR2"
    file_path = dir2_path / "SIMPLE-FILE"
    (source_package_root_path / dir2_path).mkdir(parents=True)
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 4
    assert plan[dir1_path] == PlanNode(
        Action.NONE, False, dir1_path, dir1_path, True
    )
    assert plan[dir2_path] == PlanNode(
        Action.NONE, False, dir2_path, dir2_path, True
    )
    assert plan[file_path].action == Action.NONE


def test_plan_paths_dir_with_hidden_file(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path("SIMPLE-DIR")
    file_path = dir_path / ".HIDDEN-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 3
    assert plan[dir_path] == PlanNode(Action.NONE, False, dir_path, dir_path, True)
    assert plan[file_path].action == Action.NONE


def test_plan_paths_dir_with_renamed_file(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path("SIMPLE-DIR")
    file_path = dir_path / "dot-SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 3
    assert plan[dir_path] == PlanNode(Action.NONE, False, dir_path, dir_path, True)
    assert plan[file_path] == PlanNode(
        Action.NONE, True, file_path, dir_path / ".SIMPLE-FILE", False
    )


def test_plan_paths_hidden_dir(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path(".HIDDEN-DIR")
    file_path = dir_path / "SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 3
    assert plan[dir_path] == PlanNode(Action.NONE, False, dir_path, dir_path, True)
    assert plan[file_path].action == Action.NONE


def test_plan_paths_renamed_dir(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path("dot-SIMPLE-DIR")
    file_path = dir_path / "SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 3
    assert plan[dir_path] == PlanNode(
        Action.NONE, True, dir_path, Path(".SIMPLE-DIR"), True
    )
    assert plan[file_path].action == Action.NONE


def test_plan_paths_several_normal_files(tmp_path):
    source_package_root_path = tmp_path
    file1_path = Path("SIMPLE-FILE1")
    file2_path = Path("SIMPLE-FILE2")
    file3_path = Path("SIMPLE-FILE3")
    (source_package_root_path / file1_path).touch()
    (source_package_root_path / file2_path).touch()
    (source_package_root_path / file3_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 4
    assert plan[file1_path] == PlanNode(
        Action.NONE, False, file1_path, file1_path, False
    )
    assert plan[file2_path] == PlanNode(
        Action.NONE, False, file2_path, file2_path, False
    )
    assert plan[file3_path] == PlanNode(
        Action.NONE, False, file3_path, file3_path, False
    )


def test_plan_paths_dir_containing_several_files(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path("SIMPLE-DIR")
    file1_path = dir_path / "SIMPLE-FILE1"
    file2_path = dir_path / "SIMPLE-FILE2"
    file3_path = dir_path / "SIMPLE-FILE3"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file1_path).touch()
    (source_package_root_path / file2_path).touch()
    (source_package_root_path / file3_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 5
    assert plan[dir_path] == PlanNode(Action.NONE, False, dir_path, dir_path, True)
    assert plan[file1_path].action == Action.NONE
    assert plan[file2_path].action == Action.NONE
    assert plan[file3_path].action == Action.NONE


def test_plan_paths_dir_containing_several_files_including_rename(tmp_path):
    source_package_root_path = tmp_path
    dir_path = Path("SIMPLE-DIR")
    file1_path = dir_path / "dot-SIMPLE-FILE1"
    file2_path = dir_path / "SIMPLE-FILE2"
    file3_path = dir_path / "SIMPLE-FILE3"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file1_path).touch()
    (source_package_root_path / file2_path).touch()
    (source_package_root_path / file3_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 5
    assert plan[dir_path] == PlanNode(Action.NONE, False, dir_path, dir_path, True)
    assert plan[file1_path].action == Action.NONE
    assert plan[file1_path].requires_rename
    assert plan[file2_path].action == Action.NONE
    assert plan[file3_path].action == Action.NONE


def test_plan_paths_renamed_dir_inside_renamed_dir(tmp_path):
    source_package_root_path = tmp_path
    dir1_path = Path("dot-SIMPLE-DIR1")
    dir2_path = dir1_path / "dot-SIMPLE-DIR2"
    file_path = dir2_path / "SIMPLE-FILE"
    (source_package_root_path / dir2_path).mkdir(parents=True)
    (source_package_root_path / file_path).touch()

    plan = plan_install_paths(source_package_root_path)

    assert len(plan) == 4
    assert plan[dir1_path] == PlanNode(
        Action.NONE, True, dir1_path, Path(".SIMPLE-DIR1"), True
    )
    assert plan[dir2_path] == PlanNode(
        Action.NONE, True, dir2_path, Path(".SIMPLE-DIR1/.SIMPLE-DIR2"), True
    )
    assert plan[file_path].action == Action.NONE


def test_install_nothing(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    plan = plan_install(source_package_root, destination_root)

    assert len(plan) == 0


def test_install_normal_file(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    file_path = Path("SIMPLE-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 1
    assert plan[file_path] == PlanNode(
        Action.LINK, False, file_path, file_path, False
    )


def test_install_normal_file_fail(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    destination_root_path = destination_root
    file_path = Path("SIMPLE-FILE")
    (source_package_root_path / file_path).touch()
    (destination_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 1
    assert plan[file_path] == PlanNode(
        Action.FAIL, False, file_path, file_path, False
    )


def test_install_symlink_to_wrong_target_fails(tmp_path):
    """Test that existing symlink pointing to wrong target is marked FAIL."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    file_path = Path("file1")
    (source_package_root / file_path).write_text("content")

    # Create a symlink pointing to a different location
    wrong_target = tmp_path / "wrong_target"
    wrong_target.write_text("wrong content")
    (destination_root / file_path).symlink_to(wrong_target)

    plan = plan_install(source_package_root, destination_root)

    assert plan[file_path].action == Action.FAIL


def test_install_broken_symlink_fails(tmp_path):
    """Test that existing broken symlink is marked FAIL."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    file_path = Path("file1")
    (source_package_root / file_path).write_text("content")

    # Create a broken symlink (target doesn't exist)
    (destination_root / file_path).symlink_to("/nonexistent/path")

    plan = plan_install(source_package_root, destination_root)

    assert plan[file_path].action == Action.FAIL


def test_install_symlink_to_our_source_skips(tmp_path):
    """Test that existing symlink pointing to our source is marked SKIP."""
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    file_path = Path("file1")
    (source_package_root / file_path).write_text("content")

    # Create a symlink pointing to our source (already installed)
    (destination_root / file_path).symlink_to(source_package_root / file_path)

    plan = plan_install(source_package_root, destination_root)

    assert plan[file_path].action == Action.SKIP


def test_install_hidden_file(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    file_path = Path(".HIDDEN-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 1
    assert plan[file_path] == PlanNode(
        Action.LINK, False, file_path, file_path, False
    )


def test_install_file_with_renaming(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    file_path = Path("dot-SIMPLE-FILE")
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 1
    assert plan[file_path] == PlanNode(
        Action.LINK, True, file_path, Path(".SIMPLE-FILE"), False
    )


def test_install_dir(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path("SIMPLE-DIR")
    file_path = dir_path / "SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 2
    assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
    assert plan[file_path].action == Action.SKIP


def test_install_dir_inside_dir(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir1_path = Path("SIMPLE-DIR1")
    dir2_path = dir1_path / "SIMPLE-DIR2"
    file_path = dir2_path / "SIMPLE-FILE"
    (source_package_root_path / dir2_path).mkdir(parents=True)
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 3
    assert plan[dir1_path] == PlanNode(
        Action.LINK, False, dir1_path, dir1_path, True
    )
    assert plan[dir2_path] == PlanNode(
        Action.SKIP, False, dir2_path, dir2_path, True
    )
    assert plan[file_path].action == Action.SKIP


def test_install_dir_with_hidden_file(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path("SIMPLE-DIR")
    file_path = dir_path / ".HIDDEN-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 2
    assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
    assert plan[file_path].action == Action.SKIP


def test_install_dir_with_renamed_file(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path("SIMPLE-DIR")
    file_path = dir_path / "dot-SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 2
    assert plan[dir_path] == PlanNode(
        Action.CREATE, False, dir_path, dir_path, True
    )
    assert plan[file_path] == PlanNode(
        Action.LINK, True, file_path, dir_path / ".SIMPLE-FILE", False
    )


def test_install_hidden_dir(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path(".HIDDEN-DIR")
    file_path = dir_path / "SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 2
    assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
    assert plan[file_path].action == Action.SKIP


def test_install_renamed_dir(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path("dot-SIMPLE-DIR")
    file_path = dir_path / "SIMPLE-FILE"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 2
    assert plan[dir_path] == PlanNode(
        Action.LINK, True, dir_path, Path(".SIMPLE-DIR"), True
    )
    assert plan[file_path].action == Action.SKIP


def test_install_several_normal_files(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    file1_path = Path("SIMPLE-FILE1")
    file2_path = Path("SIMPLE-FILE2")
    file3_path = Path("SIMPLE-FILE3")
    (source_package_root_path / file1_path).touch()
    (source_package_root_path / file2_path).touch()
    (source_package_root_path / file3_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 3
    assert plan[file1_path] == PlanNode(
        Action.LINK, False, file1_path, file1_path, False
    )
    assert plan[file2_path] == PlanNode(
        Action.LINK, False, file2_path, file2_path, False
    )
    assert plan[file3_path] == PlanNode(
        Action.LINK, False, file3_path, file3_path, False
    )


def test_install_dir_containing_several_files(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path("SIMPLE-DIR")
    file1_path = dir_path / "SIMPLE-FILE1"
    file2_path = dir_path / "SIMPLE-FILE2"
    file3_path = dir_path / "SIMPLE-FILE3"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file1_path).touch()
    (source_package_root_path / file2_path).touch()
    (source_package_root_path / file3_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 4
    assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
    assert plan[file1_path].action == Action.SKIP
    assert plan[file2_path].action == Action.SKIP
    assert plan[file3_path].action == Action.SKIP


def test_install_dir_containing_several_files_including_rename(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir_path = Path("SIMPLE-DIR")
    file1_path = dir_path / "dot-SIMPLE-FILE1"
    file2_path = dir_path / "SIMPLE-FILE2"
    file3_path = dir_path / "SIMPLE-FILE3"
    (source_package_root_path / dir_path).mkdir()
    (source_package_root_path / file1_path).touch()
    (source_package_root_path / file2_path).touch()
    (source_package_root_path / file3_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 4
    assert plan[dir_path] == PlanNode(
        Action.CREATE, False, dir_path, dir_path, True
    )
    assert plan[file1_path].action == Action.LINK
    assert plan[file1_path].requires_rename
    assert plan[file2_path].action == Action.LINK
    assert plan[file3_path].action == Action.LINK


def test_install_renamed_dir_inside_renamed_dir(tmp_path):
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()
    source_package_root_path = source_package_root
    dir1_path = Path("dot-SIMPLE-DIR1")
    dir2_path = dir1_path / "dot-SIMPLE-DIR2"
    file_path = dir2_path / "SIMPLE-FILE"
    (source_package_root_path / dir2_path).mkdir(parents=True)
    (source_package_root_path / file_path).touch()

    plan = plan_install(source_package_root_path, destination_root)

    assert len(plan) == 3
    assert plan[dir1_path] == PlanNode(
        Action.CREATE, True, dir1_path, Path(".SIMPLE-DIR1"), True
    )
    assert plan[dir2_path] == PlanNode(
        Action.LINK, True, dir2_path, Path(".SIMPLE-DIR1/.SIMPLE-DIR2"), True
    )
    assert plan[file_path].action == Action.SKIP


def test_install_deep_nesting_with_renamed_leaf(tmp_path):
    """
    Test that deeply nested directories with a renamed file at the leaf install correctly.

    This tests the fix for a bug where:
    - Deep directory structure: a/b/c/d/e/f/dot-deepfile
    - The leaf file needs renaming (dot-deepfile -> .deepfile)
    - Directory f gets marked CREATE (because child needs renaming)
    - All parent directories should also be CREATE (via mark_all_ancestors)

    Bug was: parent dirs were overwritten to LINK when processed bottom-up,
    causing FileExistsError when we tried to CREATE f under a symlinked parent.

    Fix: preserve CREATE if already set by a descendant's mark_all_ancestors.
    """
    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create deep nesting: a/b/c/d/e/f/dot-deepfile
    deep_path = Path("a/b/c/d/e/f")
    file_path = deep_path / "dot-deepfile"
    (source_package_root / deep_path).mkdir(parents=True)
    (source_package_root / file_path).write_text("deep content")

    plan = plan_install(source_package_root, destination_root)

    # All directories should be CREATE (to support the renamed file at the leaf)
    for part_count in range(1, 7):  # a, b, c, d, e, f
        parts = ["a", "b", "c", "d", "e", "f"][:part_count]
        subdir_path = Path("/".join(parts))
        assert plan[subdir_path].action == Action.CREATE, f"{subdir_path} should be CREATE"

    # The file should be LINK with renaming
    assert plan[file_path].action == Action.LINK
    assert plan[file_path].requires_rename
    assert plan[file_path].relative_destination_path == Path("a/b/c/d/e/f/.deepfile")


def test_install_deep_nesting_execute(tmp_path, isolated_db):
    """
    Test that deeply nested directories with renamed leaf actually install without error.

    This is an integration test that verifies the full install flow works,
    not just the planning phase.
    """
    from typer.testing import CliRunner

    from dotx.cli import app

    source_package_root = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_package_root.mkdir()
    destination_root.mkdir()

    # Create deep nesting: a/b/c/d/e/f/dot-deepfile
    deep_path = Path("a/b/c/d/e/f")
    file_path = deep_path / "dot-deepfile"
    (source_package_root / deep_path).mkdir(parents=True)
    (source_package_root / file_path).write_text("deep content")

    runner = CliRunner()

    # Execute install via CLI - should not raise an error
    result = runner.invoke(app, [f"--target={destination_root}", "install", str(source_package_root)])

    assert result.exit_code == 0, f"Install failed: {result.output}"

    # Verify: all directories should be real directories (CREATE), not symlinks
    for part_count in range(1, 7):
        parts = ["a", "b", "c", "d", "e", "f"][:part_count]
        dir_path = destination_root / "/".join(parts)
        assert dir_path.is_dir(), f"{dir_path} should be a directory"
        assert not dir_path.is_symlink(), f"{dir_path} should NOT be a symlink"

    # The file should be a symlink with the renamed name (.deepfile, not dot-deepfile)
    deep_file_dest = destination_root / "a/b/c/d/e/f/.deepfile"
    assert deep_file_dest.is_symlink()
    assert deep_file_dest.exists()
    assert deep_file_dest.read_text() == "deep content"


# --- XDG Mode Tests ---


def test_resolve_destination_no_xdg():
    """Test that resolve_destination without XDG mode just joins paths."""
    from dotx.plan import resolve_destination

    default_root = Path("/home/user")
    relative_path = Path(".config/app/config.toml")

    result = resolve_destination(relative_path, default_root, xdg_mode=False)

    assert result == Path("/home/user/.config/app/config.toml")


def test_resolve_destination_xdg_config(monkeypatch):
    """Test that resolve_destination with XDG mode redirects .config paths."""
    from dotx.plan import resolve_destination

    # Set custom XDG_CONFIG_HOME
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")

    default_root = Path("/home/user")
    relative_path = Path(".config/app/config.toml")

    result = resolve_destination(relative_path, default_root, xdg_mode=True)

    assert result == Path("/custom/config/app/config.toml")


def test_resolve_destination_xdg_data(monkeypatch):
    """Test that resolve_destination with XDG mode redirects .local/share paths."""
    from dotx.plan import resolve_destination

    # Set custom XDG_DATA_HOME
    monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")

    default_root = Path("/home/user")
    relative_path = Path(".local/share/app/data.db")

    result = resolve_destination(relative_path, default_root, xdg_mode=True)

    assert result == Path("/custom/data/app/data.db")


def test_resolve_destination_xdg_cache(monkeypatch):
    """Test that resolve_destination with XDG mode redirects .cache paths."""
    from dotx.plan import resolve_destination

    # Set custom XDG_CACHE_HOME
    monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache")

    default_root = Path("/home/user")
    relative_path = Path(".cache/app/cache.db")

    result = resolve_destination(relative_path, default_root, xdg_mode=True)

    assert result == Path("/custom/cache/app/cache.db")


def test_resolve_destination_xdg_non_xdg_path(monkeypatch):
    """Test that paths not matching XDG prefixes still use default_root in XDG mode."""
    from dotx.plan import resolve_destination

    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")

    default_root = Path("/home/user")
    relative_path = Path(".bashrc")

    result = resolve_destination(relative_path, default_root, xdg_mode=True)

    assert result == Path("/home/user/.bashrc")


def test_resolve_destination_xdg_exact_match(monkeypatch):
    """Test that exact XDG prefix paths resolve to XDG directory itself."""
    from dotx.plan import resolve_destination

    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")

    default_root = Path("/home/user")
    relative_path = Path(".config")

    result = resolve_destination(relative_path, default_root, xdg_mode=True)

    assert result == Path("/custom/config")
