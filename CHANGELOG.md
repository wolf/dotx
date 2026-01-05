# Changelog

All notable changes to dotx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.1.1] - 2026-01-05

### Fixed
- **Critical bug**: `dotx list` now shows semantic package names instead of implementation details like "dot-config"
- `dotx sync --package-root` now correctly infers package names as the first directory component under package root
- `dotx list` output now matches README documentation (shows full package paths)

## [3.1.0] - 2026-01-05

### Added
- **`dotx path` command**: Get source path of installed packages for Unix composition (`tree $(dotx path bash)`)
- **`dotx which` command**: Find which package owns a target file (`dotx which ~/.bashrc`)
- Support for `--package-root` filter in `dotx path` to disambiguate packages

### Fixed
- Database schema v1 detection now happens before attempting to apply v2 schema, preventing confusing SQLite errors
- Clear error message with upgrade instructions when v1 database is detected

## [3.0.0] - 2026-01-05

### Added
- **Always-create patterns**: Shared directories like `.config` are now automatically created as real directories instead of symlinks, allowing multiple packages to install files into them
- Built-in always-create patterns for XDG directories (`.config`, `.local/share`, `.local/bin`, `.cache`)
- Built-in always-create patterns for security-sensitive directories (`.ssh`, `.gnupg`)
- Support for custom always-create patterns via `.always-create` files (package-local and user-global at `~/.config/dotx/always-create`)
- Hierarchical pattern matching system with precedence: built-in → user config → package-local
- Built-in `.dotxignore` patterns (replaces hardcoded ignore list)
- 15 comprehensive tests for always-create functionality

### Changed
- **Database schema upgraded to v2** with new columns for package identity tracking:
  - `package_root`: Root directory containing all dotfiles
  - `package_name`: Semantic package name (e.g., `helix` instead of `helix/dot-config`)
  - `source_package_root`: Full path to package source
- Database automatically migrates from v1 to v2 on first access (no user action needed)
- Install logic now checks always-create patterns at exact depth (prevents subdirectory matches)
- Refactored `IgnoreRules` to use new `HierarchicalPatternMatcher` class
- Improved pattern matching to support gitignore-style patterns with proper precedence

### Fixed
- Shared directories like `.config` can now be used by multiple packages correctly
- Package names in database now reflect semantic names instead of implementation details
- Directory patterns (e.g., `node_modules/`) now match correctly with trailing slashes

### Migration Notes
**Upgrading from v2.x (schema v1):**

The v1 database schema is no longer supported. If you have an existing v1 database, dotx will detect this and display upgrade instructions.

To upgrade:
1. Delete the old database: `rm ~/.local/share/dotx/installed.db`
2. Rebuild it from your existing installations:
   ```bash
   dotx sync --package-root ~/dotfiles
   ```

If you previously had issues with multiple packages trying to use `.config`, reinstalling will fix it:
```bash
dotx uninstall --all
dotx install [your-packages]
```

## [2.2.1] - 2026-01-03

### Fixed
- **Critical bug**: `.dotxignore` files now properly combine patterns from all hierarchy levels (global → parents → closest) instead of only using the closest file. This fixes nested `.dotxignore` files not working correctly and enables proper pattern overriding with negation patterns (`!pattern`).

## [2.2.0] - 2026-01-03

### Added
- `sync` command now supports `--package-root` flag to filter packages to specific directories
- `sync` command now supports `--clean` flag to remove orphaned database entries (like `git fetch --prune`)

### Changed
- Internal: Refactored CLI into commands package for better code organization

## [2.1.0] - 2026-01-03

### Added
- Rich terminal output with colored tables, progress bars, and spinners
- Smart scanning with progress UI for `sync` command
- Visual feedback during install and uninstall operations

### Changed
- `list` command now displays results in formatted tables
- All commands provide better visual feedback and status indicators

## [2.0.4] - 2026-01-03

### Fixed
- Include `installed-schema.sql` in package distribution for proper installation

## [2.0.3] - 2026-01-03

### Changed
- Show help text when `dotx` is run without arguments (instead of error)

## [2.0.2] - 2026-01-03

### Added
- `--version` and `-V` flags to display version information

## [2.0.1] - 2026-01-03

### Fixed
- License deprecation warnings in package metadata
- Updated project status to Production/Stable

## [2.0.0] - 2026-01-03

### Changed
- **BREAKING:** Database location moved to XDG_DATA_HOME (`~/.local/share/dotx/installed.db`)
- Removed automatic migration code from older database locations

### Migration Notes
If upgrading from v1.x, manually move your database:
```bash
mkdir -p ~/.local/share/dotx
mv ~/.dotx/installed.db ~/.local/share/dotx/
```

Or rebuild the database using `dotx sync --package-root ~/dotfiles`

## [1.1.0] - 2026-01-02

### Added
- Comprehensive test coverage (77.64%, up from 53%)
- 21 new integration tests for database commands
- Automated coverage tracking with pytest-cov
- HTML coverage reports

### Fixed
- Database now correctly stores symlink paths instead of resolved paths

### Changed
- Development: Added coverage tracking and pre-commit hooks documentation

## [1.0.0] - 2025-12-01

### Added
- SQLite installation database to track which packages installed which files
- `list` command to show all installed packages with file counts
- `list --as-commands` to export reinstall commands for migration
- `verify` command to check installations match the filesystem
- `show` command to display detailed package installation information
- `sync` command to rebuild database from existing symlinks
- `.dotxignore` files for gitignore-style pattern matching
- Nested `.dotxignore` files in subdirectories
- Global ignore file at `~/.config/dotx/ignore`
- Negation patterns in ignore files (`!important.conf`)
- Database location respects `XDG_DATA_HOME` environment variable

### Changed
- **BREAKING:** Removed `-i/--ignore` command-line option in favor of `.dotxignore` files

### Migration from older versions
Replace command-line ignore patterns with `.dotxignore` files:
```bash
# Old way:
dotx --ignore=README.* --ignore=.mypy_cache install bash

# New way:
cat > bash/.dotxignore <<EOF
README.*
.mypy_cache
EOF
dotx install bash
```

[Unreleased]: https://github.com/wolf/dotx/compare/v3.1.1...HEAD
[3.1.1]: https://github.com/wolf/dotx/compare/v3.1.0...v3.1.1
[3.1.0]: https://github.com/wolf/dotx/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/wolf/dotx/compare/v2.2.1...v3.0.0
[2.2.1]: https://github.com/wolf/dotx/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/wolf/dotx/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/wolf/dotx/compare/v2.0.4...v2.1.0
[2.0.4]: https://github.com/wolf/dotx/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/wolf/dotx/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/wolf/dotx/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/wolf/dotx/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/wolf/dotx/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/wolf/dotx/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/wolf/dotx/releases/tag/v1.0.0
