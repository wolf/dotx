## The Basic Idea

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

`dotx` tracks all installations in a SQLite database at `~/.config/dotx/installed.db` (or `$XDG_CONFIG_HOME/dotx/installed.db`). This enables better package management and verification.

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

#### Rebuild database from filesystem

If you have existing dotfile installations and an empty or missing database, use `sync` to rebuild it:

```bash
# Preview what would be added to database
+$ dotx sync --dry-run

# Interactively rebuild database from filesystem
+$ dotx sync
Found 15 symlink(s) in /Users/wolf

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

The `sync` command scans your home directory for symlinks and attempts to determine which package they belong to, then rebuilds the database accordingly.

### How it works

*Documentation to be expanded*

### What's New in v1.1.0

#### Testing and Quality
- **Comprehensive test coverage**: 77.64% overall (up from 53%)
- **21 new database command tests**: Full integration testing for `list`, `verify`, `show`, `sync`
- **Automated coverage tracking**: pytest-cov integration with HTML reports
- **Bug fix**: Database now correctly stores symlink paths instead of resolved paths

#### Documentation
- Added Development section with testing, pre-commit hooks, and integration testing docs
- Added clean-up instructions for development artifacts
- Coverage reports available via `open htmlcov/index.html`

### What's New in v1.0.0

#### Installation Database
- **SQLite database** tracks which packages installed which files
- **New commands**: `list`, `verify`, `show`, `sync` for package management
- Database location respects `XDG_CONFIG_HOME` environment variable
- Export reinstall commands with `dotx list --as-commands` for easy migration

#### Improved Ignore System
- **`.dotxignore` files** replace CLI `-i/--ignore` option (breaking change)
- Full gitignore-style pattern syntax support
- Nested `.dotxignore` files in subdirectories
- Global ignore file at `~/.config/dotx/ignore`
- Negation patterns (`!important.conf`)

#### Quality Improvements
- Pre-commit hooks with ruff, pyrefly, pytest
- Modern Python type annotations throughout
- Better logging with loguru
- Comprehensive code documentation and comments

### Migration from older versions

**Breaking change in v1.0.0:** The `-i/--ignore` command-line option has been removed in favor of `.dotxignore` files.

If you were using:
```bash
dotx --ignore=README.* --ignore=.mypy_cache install bash
```

Now create a `.dotxignore` file in your package:
```bash
+$ cat > bash/.dotxignore <<EOF
README.*
.mypy_cache
EOF

+$ dotx install bash
```

Or use the global ignore file at `~/.config/dotx/ignore` for patterns that apply to all packages.

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

### What's next

Potential future enhancements:
* Support for templates and variable substitution in dotfiles
* Hooks system for running commands before/after installation
* Conflict resolution strategies for overlapping packages
* Shell completions for bash/zsh/fish
