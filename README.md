## The Basic Idea

> **Comparing dotfile managers?** See [ALTERNATIVES.md](ALTERNATIVES.md) for a detailed comparison of dotx vs GNU Stow, chezmoi, YADM, dotbot, and others.

### What `dotx` does; what it's _for_
#### The problem

You're a software developer with tons of _dotfiles_: `.bashrc`, `.vimrc`, `.tmux.conf`, `.inputrc`, and things living in
`.config` just to name a few.  You have to install these on every system you work on **and** keep them up-to-date as
they change.  Without some special setup, there's no one source of truth, no easy deploy, no version control.  The
obvious answer is to keep them in a `git` repo, but making your home directory _be_ that repo is no good.  And maybe you
don't even want them to live together.  Your `bash` files should be in a group, your `vim` files in a group, etc.

#### A solution

The solution is obvious: keep them in a git repo, divided up into packages (or multiple `git` repos if you prefer), and
install links in your home directory (or the _target_ directory) that point _into_ your `git` repo, at the source of
truth files.

The solution is so obvious in fact that of course there is already a `perl` tool called GNU `stow` that helps you do
exactly that.  GNU `stow` has a feature that you can ask it to rename files that look like this: `"dot-bashrc"` to this
`".bashrc"`.  This is incredibly helpful if, for instance, you want to edit your dotfiles on your iPad and your editor
of choice can't see files or directories that start with a  `"."`.  Keeping your files in this form means no invisible
files in your source repo so you can edit anywhere with anything.

Unfortunately, GNU `stow` has a bug that its renaming feature doesn't work on directories.  And it's also a very general
purpose tool.  It's made for installing a link-farm to any kind of package from anywhere to anywhere.

`dotx` is a simple tool with a simple goal: manage a link-farm of possibly renamed links to dotfiles.  Yes, you can use
it for other purposes, but it's tuned for its goal.  It does the renaming task if you want it, but if your source files
are named simply `.bashrc` it works just as well.

### The user interface
```
Usage: dotx [OPTIONS] COMMAND [ARGS]...

  Manage a link farm: (un)install groups of links from "source packages".

Options:
  --debug / --no-debug
  --verbose / --quiet
  --log FILE                Where to write the log (defaults to stderr)
  --target DIRECTORY        Where to install (defaults to $HOME)
  --dry-run / --no-dry-run  Just echo; don't actually (un)install.
  --help                    Show this message and exit.

Commands:
  install    install [source-package...]
  uninstall  uninstall [source-package...]
  list       List all installed packages
  verify     Verify installations against filesystem
  show       Show detailed installation information for a package
  path       Get source path of an installed package
  which      Find which package owns a target file
  sync       Rebuild database from filesystem (interactive)
```
So if you had a source package (a directory containing files) named `"bash"` containing `"dot-bashrc"` and
`"dot-bash_profile"` you could install links to those two files (named `".bashrc"` and `".bash_profile"`) into your
`${HOME}` directory by being in the parent of the source package and saying:
```bash
+$ pwd
/Users/wolf/builds/dotfiles

+$ ls -1
bash
tmux
vim

+$ tree -aL 1 bash
bash
├── README.md
├── dot-bash_profile
├── dot-bash_tools.bin
├── dot-bash_topics.d
└── dot-bashrc


+$ dotx install bash

+$ ls -al ~
...
lrwxr--r--    37 wolf 19 Jul 11:01 .bash_profile -> builds/dotfiles/bash/dot-bash_profile
lrwxr--r--    39 wolf 19 Jul 11:01 .bash_tools.bin -> builds/dotfiles/bash/dot-bash_tools.bin/
lrwxr--r--    38 wolf 19 Jul 11:01 .bash_topics.d -> builds/dotfiles/bash/dot-bash_topics.d/
lrwxr--r--    31 wolf 19 Jul 11:01 .bashrc -> builds/dotfiles/bash/dot-bashrc
...
```

### Ignoring files with `.dotxignore`

If you've got some files in your source package that don't need to be linked, you can create a `.dotxignore` file in
your package directory. This file works just like `.gitignore` and supports the same pattern syntax:

```bash
# In your package directory, create .dotxignore:
+$ cat > bash/.dotxignore <<EOF
README.*
.mypy_cache
*.tmp
EOF

+$ dotx install bash tmux vim
```

The `.dotxignore` file supports:
- Glob patterns (`*.log`, `*.tmp`)
- Directory patterns (`node_modules/`, `__pycache__/`)
- Negation patterns (`!important.conf`)
- Comments (lines starting with `#`)
- Root-only patterns (`/.git` matches only at package root)

You can also nest `.dotxignore` files in subdirectories, just like `.gitignore`. Files closer to the matched file take
precedence.

#### Global ignore file

Create a global ignore file at `~/.config/dotx/ignore` to exclude patterns from all packages:

```bash
+$ mkdir -p ~/.config/dotx
+$ cat > ~/.config/dotx/ignore <<EOF
# Ignore these in all packages
.DS_Store
.git/
*.log
*.tmp
__pycache__/
node_modules/
EOF
```

Uninstall looks almost just like install:
```bash
dotx uninstall bash vim tmux
```

### Installation Database

`dotx` tracks all installations in a SQLite database at `~/.local/share/dotx/installed.db` (or `$XDG_DATA_HOME/dotx/installed.db`). This enables better package management and verification.

#### List installed packages

See all installed packages with file counts and installation dates:

```bash
+$ dotx list

Installed Packages:
--------------------------------------------------------------------------------
Package                                            Files      Last Install
--------------------------------------------------------------------------------
/Users/wolf/builds/dotfiles/bash                   12         2026-01-02 14:23:11
/Users/wolf/builds/dotfiles/tmux                   3          2026-01-02 14:23:15
/Users/wolf/builds/dotfiles/vim                    8          2026-01-02 14:23:18
--------------------------------------------------------------------------------
Total: 3 package(s)
```

Export as reinstall commands for easy migration:

```bash
+$ dotx list --as-commands
dotx install /Users/wolf/builds/dotfiles/bash
dotx install /Users/wolf/builds/dotfiles/tmux
dotx install /Users/wolf/builds/dotfiles/vim
```

#### Verify installations

Check that database records match the filesystem:

```bash
+$ dotx verify

✓ All installations verified successfully.
```

Or verify a specific package:

```bash
+$ dotx verify bash

/Users/wolf/builds/dotfiles/bash:
  /Users/wolf/.bashrc
    Issue: File missing (in DB but not on filesystem)
    Expected type: file

⚠ Found 1 issue(s).
```

#### Show package details

View detailed information about a specific package:

```bash
+$ dotx show bash

Package: /Users/wolf/builds/dotfiles/bash
Installed files: 12

Installations:
--------------------------------------------------------------------------------

  Target: /Users/wolf/.bash_profile
  Type:   file
  When:   2026-01-02T14:23:11.234567

  Target: /Users/wolf/.bashrc
  Type:   file
  When:   2026-01-02T14:23:11.456789

  Target: /Users/wolf/.bash_topics.d
  Type:   directory
  When:   2026-01-02T14:23:11.678901
...
```

#### Get package source path

Get the source path of an installed package for composition with other Unix tools:

```bash
+$ dotx path bash
/Users/wolf/builds/dotfiles/bash

# Compose with other tools
+$ tree $(dotx path bash)
/Users/wolf/builds/dotfiles/bash
├── dot-bash_profile
├── dot-bash_topics.d
└── dot-bashrc

+$ cd $(dotx path vim)

+$ ls -la $(dotx path helix)
```

The command prints the source directory path(s) where package files are located. If a package has files from multiple source directories (like the shells example with subdirectories), all unique paths are printed, one per line.

Exit codes: 0 if package found, 1 if not found.

#### Find which package owns a file

Find which package installed a specific file:

```bash
+$ dotx which ~/.bashrc
bash

+$ dotx which ~/.config/helix/config.toml
helix

# Compose with other commands
+$ dotx path $(dotx which ~/.vimrc)
/Users/wolf/builds/dotfiles/vim

+$ tree $(dotx path $(dotx which ~/.zshrc))
```

Simple output (just the package name) for easy composition with other Unix tools.

Exit codes: 0 if file found, 1 if not managed by any package.

#### Rebuild database from filesystem

If you have existing dotfile installations and an empty or missing database, use `sync` to rebuild it.

##### The Problem: Unwanted Symlinks

By default, `sync` scans your home directory and `~/.config` for **all** symlinks. This can discover symlinks you don't want to track as dotfiles packages, such as:
- System symlinks in `~/Library/` (macOS)
- Application symlinks in `/Applications/`
- IDE or tool-generated symlinks
- Homebrew-managed symlinks

For example, without filtering you might see:
```bash
+$ dotx sync --dry-run
✓ Found 44 symlink(s)

Discovered 25 potential package(s):
  /Users/wolf/dotfiles/bash        # ✓ Want this
    5 symlink(s)
  /Users/wolf/dotfiles/vim          # ✓ Want this
    8 symlink(s)
  /Users/wolf/Library               # ✗ Don't want this!
    1 symlink(s)
  /Applications/Raycast.app/...    # ✗ Don't want this!
    1 symlink(s)
```

##### The Solution: `--package-root`

Use `--package-root` to filter packages to **only** those under specific directories. This is **strongly recommended** to avoid tracking unwanted symlinks:

```bash
# Filter to only your dotfiles directory
+$ dotx sync --dry-run --package-root ~/dotfiles
✓ Found 44 symlink(s)
Filtered out 6 symlink(s) not under --package-root

Discovered 3 potential package(s):
  /Users/wolf/dotfiles/bash
    5 symlink(s)
  /Users/wolf/dotfiles/vim
    8 symlink(s)
  /Users/wolf/dotfiles/git
    2 symlink(s)
```

You can specify multiple roots if your packages are in different locations:

```bash
+$ dotx sync --package-root ~/dotfiles --package-root ~/work/configs
```

##### Safety Warning

If you run `sync` without `--package-root` and have an empty database, you'll see a warning:

```bash
+$ dotx sync --dry-run
✓ Found 44 symlink(s)
⚠ Warning: No --package-root specified and database is empty.
  Consider using --package-root to filter packages (e.g., --package-root ~/dotfiles)
```

##### Complete Example

```bash
# Preview what will be synced (recommended first step)
+$ dotx sync --dry-run --package-root ~/dotfiles

# After reviewing, sync for real
+$ dotx sync --package-root ~/dotfiles
✓ Found 15 symlink(s)
Filtered out 0 symlink(s) not under --package-root

Discovered 3 potential package(s):
  /Users/wolf/dotfiles/bash
    5 symlink(s)
  /Users/wolf/dotfiles/vim
    8 symlink(s)
  /Users/wolf/dotfiles/git
    2 symlink(s)

This will rebuild the database with the discovered installations.
Continue? [y/N]: y

✓ Recorded 15 installation(s) in database.
```

**Note:** The `sync` command is **additive** - it updates existing entries and adds new ones, but doesn't delete entries for packages not found. This means running sync with `--package-root` won't remove other packages from your database.

### Shared Directories: How `.config` and Friends Work

When multiple packages need to install files into the same directory (like `~/.config`), that directory must be a **real directory**, not a symlink. Otherwise, only one package could use it.

`dotx` automatically handles this using **always-create patterns** - directories that are always created as real directories instead of being symlinked.

#### Built-in Always-Create Patterns

These directories are automatically created as real directories:

**XDG Base Directories:**
- `.config` - Application configuration files
- `.local` - User-local data
- `.local/share` - User-specific data files
- `.local/bin` - User-specific executables
- `.cache` - Non-essential cached data

**Security-Sensitive Directories:**
- `.ssh` - SSH keys and configuration
- `.gnupg` - GPG keys and configuration

For example, if you have both a `vim` and `helix` package that install into `.config`:

```bash
+$ tree -L 2 dotfiles/
dotfiles/
├── vim/
│   └── dot-config/
│       └── nvim/
└── helix/
    └── dot-config/
        └── helix/

+$ dotx install vim helix

+$ ls -la ~/.config/
drwxr-xr-x  .config/         # Real directory (not a symlink!)
lrwxr-xr-x  nvim -> .../vim/dot-config/nvim/
lrwxr-xr-x  helix -> .../helix/dot-config/helix/
```

Notice that `.config` itself is a real directory, allowing both packages to install their subdirectories as symlinks within it.

#### Custom Always-Create Patterns (Advanced)

For most users, the built-in patterns are sufficient. However, if you have custom shared directories, you can create `.always-create` files using the same syntax as `.dotxignore`:

**Package-local** (in your package directory):
```bash
+$ cat > mypackage/.always-create <<EOF
# Custom shared directory
.myapp
EOF
```

**User-global** (applies to all packages):
```bash
+$ mkdir -p ~/.config/dotx
+$ cat > ~/.config/dotx/always-create <<EOF
# My custom shared directories
.workspace
.tools
EOF
```

Pattern precedence: **built-in → user global → package-local** (later patterns can override earlier ones using `!negation`)

**Note:** Patterns use leading `/` for root-level matching (e.g., `/.config` matches only `.config` at package root, not `subdir/.config`).

##### Cleaning Orphaned Entries with `--clean`

Over time, your database may accumulate **orphaned entries** - records for symlinks that no longer exist on the filesystem. Use `--clean` to remove these automatically, similar to `git fetch --prune`:

```bash
# Preview what would be cleaned
+$ dotx sync --dry-run --clean --package-root ~/dotfiles
✓ Found 15 symlink(s)

Would clean orphaned entries:
  bash: 2 orphaned entry(ies)
  vim: 1 orphaned entry(ies)
Would remove 3 orphaned entry(ies).

Dry run - no database changes made.

# Clean for real
+$ dotx sync --clean --package-root ~/dotfiles
✓ Found 15 symlink(s)
Filtered out 0 symlink(s) not under --package-root

Discovered 3 potential package(s):
  /Users/wolf/dotfiles/bash
    5 symlink(s)
  ...

This will rebuild the database with the discovered installations.
Continue? [y/N]: y

✓ Recorded 15 installation(s) in database.

Cleaning orphaned entries...
✓ Removed 3 orphaned entry(ies).
```

**When to use `--clean`:**
- After manually removing symlinks
- After uninstalling packages without using `dotx uninstall`
- During regular maintenance to keep database accurate
- When migrating or reorganizing dotfiles

**Important:** `--clean` removes database entries for files that don't exist. Always preview with `--dry-run` first to ensure you're not removing entries you want to keep.

### How it works

*Documentation to be expanded*

### Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## Development

### Running Tests

dotx uses pytest for testing with coverage tracking:

```bash
# Run all tests with coverage report
pytest

# Run specific test file
pytest tests/test_install.py

# Run tests without coverage
pytest --no-cov

# View detailed HTML coverage report
pytest && open htmlcov/index.html
```

Current test coverage is tracked and reported automatically. The coverage report shows:
- Line coverage percentage for each module
- Branch coverage for conditional statements
- Missing lines that need test coverage

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Install hooks (one-time setup)
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files
```

Hooks include:
- **ruff**: Linting and formatting
- **pyrefly**: Type checking
- **pytest**: All tests must pass

### Integration Testing

Tests in `tests/test_cli.py` use `CliRunner` from `typer.testing` to perform integration testing of the CLI. These tests run the entire CLI app in-process, verifying that commands work end-to-end with real filesystem operations.

### Clean Development Artifacts

Remove build, test, and coverage artifacts:

```bash
# Preview what will be removed (dry run)
git clean -fdxn

# Remove all development artifacts
git clean -fdx
```

This removes:
- `.venv/` - Virtual environment
- `.coverage` - Coverage data file
- `htmlcov/` - HTML coverage reports
- `.pytest_cache/` - Pytest cache
- `__pycache__/` - Python bytecode cache
- `*.egg-info/` - Package metadata
- `dist/` - Build distributions

**Note:** Add `.` at the end (`git clean -fdx .`) to limit cleanup to the current directory only.

### Shell Completions

dotx includes automatic shell completion via Typer:

```bash
# Install completion for your shell
dotx --install-completion

# Or show the completion script to customize it
dotx --show-completion
```

Supports Bash, Zsh, Fish, and PowerShell automatically.
