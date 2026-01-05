"""Tests for always-create functionality (directories that must be real, never symlinked)."""

from pathlib import Path

from dotx.install import plan_install
from dotx.plan import Action


def test_builtin_always_create_patterns(tmp_path):
    """Test that built-in always-create patterns force directories to be created."""
    # Create a package with .config directory
    package = tmp_path / "package"
    package.mkdir()
    config_dir = package / "dot-config"
    config_dir.mkdir()
    (config_dir / "app.conf").touch()

    # Install to destination
    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .config should be CREATE (not LINK) because it matches built-in always-create
    assert Path("dot-config") in plan
    assert plan[Path("dot-config")].action == Action.CREATE
    assert plan[Path("dot-config/app.conf")].action == Action.LINK


def test_always_create_with_nested_files(tmp_path):
    """Test that always-create directories contain linked files."""
    # Create package with nested structure in .config
    package = tmp_path / "package"
    package.mkdir()
    config_dir = package / "dot-config"
    config_dir.mkdir()
    app_dir = config_dir / "myapp"
    app_dir.mkdir()
    (app_dir / "config.json").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .config should be CREATE (real directory)
    assert plan[Path("dot-config")].action == Action.CREATE
    # myapp subdir should be LINK (whole directory)
    assert plan[Path("dot-config/myapp")].action == Action.LINK
    # config.json should be SKIP (parent will be linked)
    assert plan[Path("dot-config/myapp/config.json")].action == Action.SKIP


def test_always_create_local_share(tmp_path):
    """Test that .local/share is created (XDG base directory)."""
    # Create package with .local/share structure
    package = tmp_path / "package"
    package.mkdir()
    local_dir = package / "dot-local"
    local_dir.mkdir()
    share_dir = local_dir / "share"
    share_dir.mkdir()
    (share_dir / "data.db").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # Both .local and .local/share should be CREATE
    assert plan[Path("dot-local")].action == Action.CREATE
    assert plan[Path("dot-local/share")].action == Action.CREATE
    # The file should be LINK
    assert plan[Path("dot-local/share/data.db")].action == Action.LINK


def test_package_local_always_create(tmp_path):
    """Test that package-local .always-create file works."""
    # Create package with custom .always-create
    package = tmp_path / "package"
    package.mkdir()

    # Add custom always-create pattern
    always_create_file = package / ".always-create"
    always_create_file.write_text(".myapp\n")

    # Create .myapp directory
    myapp_dir = package / "dot-myapp"
    myapp_dir.mkdir()
    (myapp_dir / "config").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .myapp should be CREATE because of package .always-create
    assert plan[Path("dot-myapp")].action == Action.CREATE
    assert plan[Path("dot-myapp/config")].action == Action.LINK


def test_user_config_always_create(tmp_path, monkeypatch):
    """Test that user config always-create patterns work."""
    # Set up fake XDG_CONFIG_HOME
    config_home = tmp_path / "config"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    # Create user always-create config
    dotx_config = config_home / "dotx"
    dotx_config.mkdir()
    user_always_create = dotx_config / "always-create"
    user_always_create.write_text(".customdir\n")

    # Create package with .customdir
    package = tmp_path / "package"
    package.mkdir()
    custom_dir = package / "dot-customdir"
    custom_dir.mkdir()
    (custom_dir / "file.txt").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .customdir should be CREATE because of user config
    assert plan[Path("dot-customdir")].action == Action.CREATE
    assert plan[Path("dot-customdir/file.txt")].action == Action.LINK


def test_always_create_precedence(tmp_path, monkeypatch):
    """Test that package always-create can override by negation."""
    # Set up user config that forces .mydir to be created
    config_home = tmp_path / "config"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    dotx_config = config_home / "dotx"
    dotx_config.mkdir()
    user_always_create = dotx_config / "always-create"
    user_always_create.write_text(".mydir\n")

    # Package tries to negate it (though this is an unusual case)
    package = tmp_path / "package"
    package.mkdir()
    package_always_create = package / ".always-create"
    package_always_create.write_text("!.mydir\n")

    mydir = package / "dot-mydir"
    mydir.mkdir()
    (mydir / "file.txt").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # Package negation should override user config, so .mydir can be LINK
    assert plan[Path("dot-mydir")].action == Action.LINK


def test_always_create_ssh_directory(tmp_path):
    """Test that .ssh directory is always created (security-sensitive)."""
    package = tmp_path / "package"
    package.mkdir()
    ssh_dir = package / "dot-ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_rsa").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .ssh should be CREATE (built-in always-create pattern)
    assert plan[Path("dot-ssh")].action == Action.CREATE
    assert plan[Path("dot-ssh/id_rsa")].action == Action.LINK


def test_always_create_with_existing_directory(tmp_path):
    """Test that always-create works when directory already exists at destination."""
    package = tmp_path / "package"
    package.mkdir()
    config_dir = package / "dot-config"
    config_dir.mkdir()
    (config_dir / "app.conf").touch()

    dest = tmp_path / "dest"
    dest.mkdir()
    # Pre-create .config at destination
    (dest / ".config").mkdir()

    plan = plan_install(package, dest)

    # .config should be EXISTS (already there) not CREATE
    assert plan[Path("dot-config")].action == Action.EXISTS
    # But file should still be LINK
    assert plan[Path("dot-config/app.conf")].action == Action.LINK


def test_always_create_multiple_levels(tmp_path):
    """Test always-create with multiple nested levels."""
    package = tmp_path / "package"
    package.mkdir()

    # Create .config/systemd structure
    config_dir = package / "dot-config"
    config_dir.mkdir()
    systemd_dir = config_dir / "systemd"
    systemd_dir.mkdir()
    user_dir = systemd_dir / "user"
    user_dir.mkdir()
    (user_dir / "myservice.service").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .config should be CREATE (always-create pattern)
    assert plan[Path("dot-config")].action == Action.CREATE
    # systemd can be LINK (whole directory)
    assert plan[Path("dot-config/systemd")].action == Action.LINK
    # user and service file should be SKIP (parent will be linked)
    assert plan[Path("dot-config/systemd/user")].action == Action.SKIP
    assert plan[Path("dot-config/systemd/user/myservice.service")].action == Action.SKIP


def test_always_create_without_rename(tmp_path):
    """Test that always-create works for directories without dot- prefix."""
    package = tmp_path / "package"
    package.mkdir()

    # Add .always-create for a directory without renaming
    always_create_file = package / ".always-create"
    always_create_file.write_text("shared\n")

    # Create shared directory (no dot- prefix)
    shared_dir = package / "shared"
    shared_dir.mkdir()
    (shared_dir / "data.txt").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # shared should be CREATE
    assert plan[Path("shared")].action == Action.CREATE
    assert plan[Path("shared/data.txt")].action == Action.LINK


def test_always_create_forces_parent_creation(tmp_path):
    """Test that renaming takes precedence over always-create patterns."""
    package = tmp_path / "package"
    package.mkdir()

    # Create nested structure where path contains .config but not at root level
    parent_dir = package / "parent"
    parent_dir.mkdir()
    config_dir = parent_dir / "dot-config"
    config_dir.mkdir()
    (config_dir / "app.conf").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # Pattern /.config only matches .config at root (depth 1), not parent/.config (depth 2)
    # However, parent must be CREATE because dot-config needs renaming
    assert plan[Path("parent")].action == Action.CREATE
    # .config inside parent should be LINK (parent is CREATE, so children are linked)
    assert plan[Path("parent/dot-config")].action == Action.LINK
    # app.conf should be SKIP (parent directory will be linked)
    assert plan[Path("parent/dot-config/app.conf")].action == Action.SKIP


def test_always_create_cache_directory(tmp_path):
    """Test that .cache directory is always created (XDG base directory)."""
    package = tmp_path / "package"
    package.mkdir()
    cache_dir = package / "dot-cache"
    cache_dir.mkdir()
    app_cache = cache_dir / "myapp"
    app_cache.mkdir()
    (app_cache / "cache.db").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .cache should be CREATE (built-in always-create)
    assert plan[Path("dot-cache")].action == Action.CREATE
    # myapp subdir can be LINK
    assert plan[Path("dot-cache/myapp")].action == Action.LINK


def test_always_create_gnupg_directory(tmp_path):
    """Test that .gnupg directory is always created (security-sensitive)."""
    package = tmp_path / "package"
    package.mkdir()
    gnupg_dir = package / "dot-gnupg"
    gnupg_dir.mkdir()
    (gnupg_dir / "pubring.kbx").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .gnupg should be CREATE (built-in always-create)
    assert plan[Path("dot-gnupg")].action == Action.CREATE
    assert plan[Path("dot-gnupg/pubring.kbx")].action == Action.LINK


def test_always_create_local_bin(tmp_path):
    """Test that .local/bin is always created (XDG base directory)."""
    package = tmp_path / "package"
    package.mkdir()
    local_dir = package / "dot-local"
    local_dir.mkdir()
    bin_dir = local_dir / "bin"
    bin_dir.mkdir()
    (bin_dir / "myscript").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # Both .local and .local/bin should be CREATE
    assert plan[Path("dot-local")].action == Action.CREATE
    assert plan[Path("dot-local/bin")].action == Action.CREATE
    # The script should be LINK
    assert plan[Path("dot-local/bin/myscript")].action == Action.LINK


def test_non_always_create_directory_can_be_linked(tmp_path):
    """Test that directories not in always-create can be symlinked."""
    package = tmp_path / "package"
    package.mkdir()

    # Create a directory that's NOT in always-create patterns
    myapp_dir = package / "dot-myapp"
    myapp_dir.mkdir()
    config_dir = myapp_dir / "config"
    config_dir.mkdir()
    (config_dir / "settings.json").touch()

    dest = tmp_path / "dest"
    dest.mkdir()

    plan = plan_install(package, dest)

    # .myapp should be LINK (whole directory can be symlinked)
    assert plan[Path("dot-myapp")].action == Action.LINK
    # Children should be SKIP (parent will be linked)
    assert plan[Path("dot-myapp/config")].action == Action.SKIP
    assert plan[Path("dot-myapp/config/settings.json")].action == Action.SKIP
