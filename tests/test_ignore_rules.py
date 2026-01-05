"""Tests for IgnoreRules class with .dotxignore file support."""

from pathlib import Path

from dotx.ignore import IgnoreRules


def test_no_ignore_files(tmp_path):
    """Test that IgnoreRules works when there are no ignore files."""
    ignore_rules = IgnoreRules(tmp_path)

    # Create a test file
    test_file = tmp_path / "file.txt"
    test_file.touch()

    # Should not be ignored (no patterns loaded)
    # But built-in patterns might still apply
    assert not ignore_rules.should_ignore(test_file)


def test_builtin_ignore_patterns(tmp_path):
    """Test that built-in ignore patterns are loaded."""
    ignore_rules = IgnoreRules(tmp_path)

    # Built-in patterns should ignore .git directories
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    assert ignore_rules.should_ignore(git_dir)

    # Built-in patterns should ignore __pycache__
    pycache_dir = tmp_path / "__pycache__"
    pycache_dir.mkdir()
    assert ignore_rules.should_ignore(pycache_dir)


def test_dotxignore_simple_pattern(tmp_path):
    """Test basic pattern matching with .dotxignore file."""
    # Create .dotxignore with simple patterns
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("*.log\n*.tmp\n")

    ignore_rules = IgnoreRules(tmp_path)

    # These should be ignored
    assert ignore_rules.should_ignore(tmp_path / "test.log")
    assert ignore_rules.should_ignore(tmp_path / "file.tmp")

    # These should not be ignored
    assert not ignore_rules.should_ignore(tmp_path / "test.txt")
    assert not ignore_rules.should_ignore(tmp_path / "file.py")


def test_dotxignore_with_comments(tmp_path):
    """Test that comments in .dotxignore are ignored."""
    # Create .dotxignore with comments
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text(
        "# This is a comment\n" "*.log\n" "# Another comment\n" "*.tmp\n"
    )

    ignore_rules = IgnoreRules(tmp_path)

    assert ignore_rules.should_ignore(tmp_path / "test.log")
    assert not ignore_rules.should_ignore(tmp_path / "test.txt")


def test_dotxignore_empty_lines(tmp_path):
    """Test that empty lines in .dotxignore are ignored."""
    # Create .dotxignore with empty lines
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("\n" "*.log\n" "\n" "*.tmp\n" "\n")

    ignore_rules = IgnoreRules(tmp_path)

    assert ignore_rules.should_ignore(tmp_path / "test.log")


def test_dotxignore_negation_pattern(tmp_path):
    """Test negation patterns (!) in .dotxignore."""
    # Create .dotxignore with negation
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("*.log\n" "!important.log\n")

    ignore_rules = IgnoreRules(tmp_path)

    # Regular .log files should be ignored
    assert ignore_rules.should_ignore(tmp_path / "test.log")

    # important.log should NOT be ignored due to negation
    assert not ignore_rules.should_ignore(tmp_path / "important.log")


def test_dotxignore_directory_pattern(tmp_path):
    """Test directory patterns in .dotxignore."""
    # Create directories
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src").mkdir()

    # Create .dotxignore
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("node_modules/\n")

    ignore_rules = IgnoreRules(tmp_path)

    assert ignore_rules.should_ignore(tmp_path / "node_modules")
    assert not ignore_rules.should_ignore(tmp_path / "src")


def test_prune_directories_basic(tmp_path):
    """Test prune_directories method."""
    # Create .dotxignore
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("build\ntmp\n")

    ignore_rules = IgnoreRules(tmp_path)

    directories = ["src", "build", "tmp", "tests"]
    pruned = ignore_rules.prune_directories(tmp_path, directories)

    assert "src" in pruned
    assert "tests" in pruned
    assert "build" not in pruned
    assert "tmp" not in pruned


def test_nested_dotxignore(tmp_path):
    """Test that nested .dotxignore files work correctly."""
    # Create root .dotxignore
    root_ignore = tmp_path / ".dotxignore"
    root_ignore.write_text("*.log\n")

    # Create subdirectory with its own .dotxignore
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    sub_ignore = subdir / ".dotxignore"
    sub_ignore.write_text("*.tmp\n")

    ignore_rules = IgnoreRules(tmp_path)

    # Root patterns should work at root
    assert ignore_rules.should_ignore(tmp_path / "test.log")

    # Subdirectory patterns should work in subdirectory
    # (both root and subdir patterns are active)
    assert ignore_rules.should_ignore(subdir / "test.tmp")
    assert ignore_rules.should_ignore(subdir / "test.log")


def test_no_dotxignore_file(tmp_path):
    """Test handling when .dotxignore doesn't exist."""
    # No .dotxignore file created
    ignore_rules = IgnoreRules(tmp_path)

    # Should still have built-in patterns
    assert ignore_rules.matcher is not None


def test_wildcard_patterns(tmp_path):
    """Test wildcard patterns like *.txt and dir/*.py."""
    # Create .dotxignore with wildcards
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("*.txt\n__pycache__\n")

    ignore_rules = IgnoreRules(tmp_path)

    assert ignore_rules.should_ignore(tmp_path / "readme.txt")
    assert ignore_rules.should_ignore(tmp_path / "notes.txt")
    assert ignore_rules.should_ignore(tmp_path / "__pycache__")
    assert not ignore_rules.should_ignore(tmp_path / "script.py")


def test_git_style_patterns(tmp_path):
    """Test git-style patterns like /root-only to match only at root."""
    # Create .dotxignore with root-only pattern
    # Note: Can't use .git because built-in patterns already ignore it everywhere
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("/root-only\n")

    ignore_rules = IgnoreRules(tmp_path)

    # root-only at root should be ignored
    root_file = tmp_path / "root-only"
    root_file.touch()
    assert ignore_rules.should_ignore(root_file)

    # root-only in subdirectory should not be ignored by root-only pattern
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    sub_file = subdir / "root-only"
    sub_file.touch()
    assert not ignore_rules.should_ignore(sub_file)


def test_precedence_package_over_builtin(tmp_path):
    """Test that package .dotxignore has higher precedence than built-in."""
    # Create .dotxignore that negates a built-in pattern
    dotxignore = tmp_path / ".dotxignore"
    # Built-in ignores .git, but we can un-ignore it
    dotxignore.write_text("!.git\n")

    ignore_rules = IgnoreRules(tmp_path)

    # .git should NOT be ignored (package pattern overrides built-in)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    assert not ignore_rules.should_ignore(git_dir)


def test_relative_path_handling(tmp_path):
    """Test that relative paths work correctly."""
    dotxignore = tmp_path / ".dotxignore"
    dotxignore.write_text("*.log\n")

    ignore_rules = IgnoreRules(tmp_path)

    # Test with relative path
    rel_path = Path("test.log")
    assert ignore_rules.should_ignore(rel_path)

    # Test with absolute path
    abs_path = tmp_path / "test.log"
    assert ignore_rules.should_ignore(abs_path)


def test_user_config_loading(tmp_path, monkeypatch):
    """Test that user config file is loaded from XDG_CONFIG_HOME."""
    # Create a fake XDG_CONFIG_HOME
    config_home = tmp_path / "config"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    # Create user dotxignore
    dotx_config = config_home / "dotx"
    dotx_config.mkdir()
    user_ignore = dotx_config / "dotxignore"
    user_ignore.write_text("*.user\n")

    # Create package root with its own patterns
    package_root = tmp_path / "package"
    package_root.mkdir()
    package_ignore = package_root / ".dotxignore"
    package_ignore.write_text("*.pkg\n")

    ignore_rules = IgnoreRules(package_root)

    # Both user and package patterns should apply
    assert ignore_rules.should_ignore(package_root / "test.user")
    assert ignore_rules.should_ignore(package_root / "test.pkg")
    assert not ignore_rules.should_ignore(package_root / "test.txt")
