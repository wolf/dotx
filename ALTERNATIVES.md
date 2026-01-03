# Dotfile Manager Alternatives

There are many dotfile management tools available. This document compares `dotx` to popular alternatives to help you choose the right tool for your needs.

## Quick Comparison

| Tool | Approach | Stars | Key Strength | Best For |
|------|----------|-------|-------------|----------|
| **dotx** | Symlinks + tracking | - | Simple, cross-platform, fixes Stow bugs | Stow users wanting bug fixes + database tracking |
| [chezmoi](https://www.chezmoi.io/) | Templates + copy | 17k+ | Templates, secrets, encryption | Complex setups with secrets/templates |
| [GNU Stow](https://www.gnu.org/software/stow/) | Symlinks | - | Mature, simple, general-purpose | Simple symlinking (if bugs don't affect you) |
| [YADM](https://yadm.io/) | Git wrapper | 6k+ | Git-native, encryption, templates | Git-first workflow, encrypted secrets |
| [dotbot](https://github.com/anishathalye/dotbot) | Config-driven | 7k+ | Declarative YAML config | Bootstrap automation |
| [rcm](https://github.com/thoughtbot/rcm) | Scripts | 3k+ | Simple shell scripts, hooks | Unix-only, hook-based workflows |

## Detailed Comparison

### GNU Stow

**What it is:** The original symlink farm manager (Perl-based, general-purpose)

**Pros:**
- Mature and stable (decades old)
- Simple concept: just creates symlinks
- No dependencies beyond Perl
- General-purpose (not just dotfiles)

**Cons:**
- **Directory rename bug**: `--dotfiles` option [doesn't work correctly with directories](https://github.com/aspiers/stow/issues/33) (creates broken symlinks)
- No installation tracking (can't list what's installed)
- No verification (can't check if installations are intact)
- No ignore file support (must manually organize packages)
- General-purpose tool, not optimized for dotfiles

**Why choose dotx instead:**
- Fixes the directory rename bug (directories work correctly)
- Installation database tracks what's installed where
- `list`, `verify`, `show` commands for package management
- `.dotxignore` files with gitignore-style patterns
- Purpose-built for dotfiles

### chezmoi

**What it is:** Template-based dotfile manager (Go-based, feature-rich)

**Pros:**
- Templates for machine-specific configurations
- Built-in secrets management (encrypted files, password manager integration)
- Rich documentation and active community
- Can handle files that need to be private, executable, or encrypted
- [Comprehensive comparison table](https://www.chezmoi.io/comparison-table/) of all tools

**Cons:**
- More complex: templates, state files, chezmoi-specific syntax
- Files are *copied* not symlinked (changes require `chezmoi apply`)
- Steeper learning curve
- Heavier weight (more features = more to learn)

**Why choose dotx instead:**
- **Simpler mental model**: just symlinks, no templates
- **Live editing**: edit files in place, see changes immediately
- **Lighter weight**: no state to manage beyond symlinks
- **Easier to understand**: directory = package, files = symlinks

**Why choose chezmoi instead:**
- Need templates for machine-specific configs
- Need encryption for secrets
- Need to run scripts on apply
- Want integrated secret management with password managers

### YADM (Yet Another Dotfile Manager)

**What it is:** Git wrapper that manages dotfiles using a bare repository

**Pros:**
- Git-native workflow (just use git commands)
- No symlinks needed (files live in their final location)
- Built-in encryption for sensitive files
- Supports alternate files for different systems
- Bootstrap script support

**Cons:**
- Uses your home directory as a git repo (can be confusing)
- Less isolation (all dotfiles in one big repo)
- Harder to share individual packages
- Files are tracked in-place (can't easily see source structure)

**Why choose dotx instead:**
- **Clear separation**: dotfiles live in dedicated directories
- **Package-based**: install/uninstall groups independently
- **Symlinks are explicit**: can see what's linked where
- **Easier to share**: share individual packages with others

**Why choose YADM instead:**
- Prefer git-first workflow
- Want files in their final location (no symlinks)
- Need built-in encryption
- Already comfortable with bare git repos

### dotbot

**What it is:** Declarative dotfile bootstrapper (Python-based, YAML config)

**Pros:**
- Declarative YAML configuration
- Not just symlinks: can run shell commands, install packages
- Good for bootstrap/setup automation
- Idempotent operations

**Cons:**
- Configuration-heavy (must define everything in YAML)
- Python dependency
- Less interactive (no `list` or `verify` commands)
- Designed for bootstrap, not ongoing management

**Why choose dotx instead:**
- **Interactive commands**: `list`, `verify`, `show`, `sync`
- **Installation tracking**: database knows what's installed
- **No config files needed**: just run `dotx install package/`
- **Better for ongoing management**: verify installations, clean orphaned entries

**Why choose dotbot instead:**
- Need complex bootstrap automation
- Want everything defined declaratively
- Need to run commands during installation

### Tuckr / lash

**What they are:** GNU Stow replacements (Rust-based)

**Pros:**
- Modern rewrites of Stow in Rust
- Fix some of Stow's bugs
- Cross-platform

**Cons:**
- Less mature than Stow
- Smaller communities
- Similar limitations to Stow (no tracking, verification)

**Why choose dotx instead:**
- Installation database with tracking
- Package management commands (`list`, `verify`, `show`)
- `.dotxignore` file support
- Sync command to rebuild database from filesystem

## When to Choose dotx

Choose **dotx** if you:

- Want a **simple symlink-based** approach (like Stow)
- Need the **directory rename bug fixed** (Stow's `--dotfiles` works for directories)
- Want **installation tracking** (see what's installed, verify integrity)
- Need **package management** (list packages, verify installations, sync database)
- Want **gitignore-style ignore patterns** (`.dotxignore` files)
- Prefer **explicit, understandable operations** (symlinks you can see)
- Want a **focused dotfiles tool** (not a general-purpose symlink manager)
- Like the **live editing workflow** (edit source files, changes are immediate)
- Work **cross-platform** (macOS, Windows, Linux) without needing templates

Choose **something else** if you:

- Need **templates** for machine-specific configs → **chezmoi**
- Need **encryption** for secrets → **chezmoi** or **YADM**
- Prefer **git-native** workflow → **YADM** or **vcsh**
- Want **declarative configuration** → **dotbot**
- Need **complex bootstrap automation** → **dotbot**

## Philosophy

**dotx** follows the Unix philosophy:

- **Do one thing well**: Manage symlink-based dotfile installations
- **Simple, composable**: Works with git, doesn't try to replace it
- **Transparent**: Symlinks are visible, operations are clear
- **Database-backed**: Track installations, verify integrity

Unlike general-purpose tools (Stow), dotx is **purpose-built for dotfiles**. Unlike feature-rich tools (chezmoi), dotx is **deliberately simple**. It finds the sweet spot: more capable than Stow, simpler than chezmoi.

## Migration Guides

### From GNU Stow

dotx is designed to be familiar to Stow users:

```bash
# Stow
stow bash
stow --dotfiles vim

# dotx (equivalent)
dotx install bash
dotx install vim
```

**Key differences:**
- dotx always renames `dot-*` → `.*` (Stow requires `--dotfiles`)
- dotx tracks installations in a database
- dotx supports `.dotxignore` files (Stow needs manual package organization)

### From chezmoi

If you're not using templates or encryption, dotx is simpler:

```bash
# Export your dotfiles from chezmoi
chezmoi archive | tar xv

# Organize into packages
mkdir -p ~/dotfiles/bash ~/dotfiles/vim
mv .bashrc ~/dotfiles/bash/
mv .vimrc ~/dotfiles/vim/

# Install with dotx
dotx install ~/dotfiles/bash ~/dotfiles/vim
```

## See Also

- [chezmoi comparison table](https://www.chezmoi.io/comparison-table/) - Comprehensive feature comparison
- [awesome-dotfiles](https://github.com/webpro/awesome-dotfiles) - Curated list of dotfile resources
- [dotfiles.github.io utilities](https://dotfiles.github.io/utilities/) - General-purpose dotfile utilities

## Sources

- [Chezmoi Comparison Table](https://www.chezmoi.io/comparison-table/)
- [GNU Stow --dotfiles bug](https://github.com/aspiers/stow/issues/33)
- [Exploring Tools For Managing Your Dotfiles](https://gbergatto.github.io/posts/tools-managing-dotfiles/)
- [awesome-dotfiles on GitHub](https://github.com/webpro/awesome-dotfiles)
- [dotfiles.github.io utilities](https://dotfiles.github.io/utilities/)
