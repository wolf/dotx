# Changelog

All notable changes to dotx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/wolf/dotx/compare/v2.2.1...HEAD
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
