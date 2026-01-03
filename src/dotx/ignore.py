"""
This module provides gitignore-style ignore rules using .dotxignore files.

Uses pathspec for pattern matching compatible with .gitignore syntax, supporting:
- Nested .dotxignore files (like .gitignore)
- Global ignore file at ~/.config/dotx/ignore
- Negation patterns (e.g., !important.conf)
- Comments (lines starting with #)

Exported class:
    IgnoreRules
"""

from pathlib import Path

import pathspec
from loguru import logger


class IgnoreRules:
    """
    Manages hierarchical .dotxignore files with gitignore-style patterns.

    Handles precedence of ignore patterns from multiple sources:
    1. .dotxignore in current directory (highest precedence)
    2. .dotxignore in parent directories
    3. Global ignore file at ~/.config/dotx/ignore (lowest precedence)

    Attributes:
        global_spec: PathSpec loaded from global ignore file, or None
        dir_specs: Cache of PathSpec objects by directory path
    """

    def __init__(self):
        """Initialize IgnoreRules and load global ignore file if it exists."""
        self.global_spec: pathspec.PathSpec | None = None
        self.dir_specs: dict[Path, pathspec.PathSpec | None] = {}

        # Load global ignore file if it exists
        global_ignore_path = Path.home() / ".config" / "dotx" / "ignore"
        if global_ignore_path.exists():
            self.global_spec = self._load_ignore_file(global_ignore_path)
            if self.global_spec:
                logger.info(f"Loaded global ignore file from {global_ignore_path}")

    def _load_ignore_file(self, ignore_file: Path) -> pathspec.PathSpec | None:
        """
        Load and parse a .dotxignore file.

        Reads the file and creates a PathSpec object for pattern matching.
        Handles comments (lines starting with #) and empty lines.
        """
        try:
            with open(ignore_file, "r") as f:
                lines = f.readlines()

            # Filter out comments and empty lines
            patterns = [
                line.rstrip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]

            if not patterns:
                return None

            # Create PathSpec using gitignore-style patterns
            return pathspec.GitIgnoreSpec.from_lines(patterns)

        except Exception as e:
            logger.warning(f"Failed to load ignore file {ignore_file}: {e}")
            return None

    def load_ignore_file(self, directory: Path) -> pathspec.PathSpec | None:
        """
        Load .dotxignore file from directory and cache it.

        Checks if directory has a .dotxignore file, loads it, and caches
        the PathSpec for future use.
        """
        # Check cache first
        if directory in self.dir_specs:
            return self.dir_specs[directory]

        # Look for .dotxignore in directory
        ignore_file = directory / ".dotxignore"
        if not ignore_file.exists():
            self.dir_specs[directory] = None
            return None

        # Load and cache
        spec = self._load_ignore_file(ignore_file)
        self.dir_specs[directory] = spec

        if spec:
            logger.info(f"Loaded .dotxignore from {directory}")

        return spec

    def get_effective_spec(
        self, path: Path, relative_to: Path
    ) -> pathspec.PathSpec | None:
        """
        Get the effective PathSpec for a path considering all ignore files.

        Combines patterns from .dotxignore files from relative_to up to path's parent,
        plus the global ignore file. Closer ignore files take precedence over global ignore.
        """
        specs = []

        # Start with global spec if available
        if self.global_spec:
            specs.append(self.global_spec)

        # Walk from relative_to up to path's parent directory
        # Collect all .dotxignore files along the way
        try:
            # Get the parent directory of the path
            if path.is_dir():
                check_dir = path
            else:
                check_dir = path.parent

            # Walk from relative_to up to check_dir, loading ignore files
            current = relative_to
            spec = self.load_ignore_file(current)
            if spec:
                specs.append(spec)

            # Walk through parent directories
            try:
                rel_path = check_dir.relative_to(relative_to)
                for part in rel_path.parts:
                    current = current / part
                    spec = self.load_ignore_file(current)
                    if spec:
                        specs.append(spec)
            except ValueError:
                # check_dir is not under relative_to
                pass

        except ValueError:
            # path is not relative to relative_to, just use global
            pass

        if not specs:
            return None

        # Combine all specs (later specs override earlier ones due to git semantics)
        # Extract patterns from all PathSpec objects and combine them
        # Patterns are already in correct order: global → parents → closest
        all_patterns = []
        for spec in specs:
            # Each PathSpec has a patterns list, extract the pattern strings
            for pattern in spec.patterns:
                all_patterns.append(pattern.pattern)  # type: ignore[attr-defined]

        # Create a new combined PathSpec with all patterns in precedence order
        return pathspec.GitIgnoreSpec.from_lines(all_patterns)

    def should_ignore(self, path: Path, relative_to: Path) -> bool:
        """
        Test if a path should be ignored.

        Checks the path against all applicable ignore rules considering
        precedence of .dotxignore files.
        """
        # Get the effective spec for this path
        spec = self.get_effective_spec(path, relative_to)

        if not spec:
            return False

        # Make path relative to relative_to for matching
        try:
            rel_path = path.relative_to(relative_to)
        except ValueError:
            # Path is not relative to relative_to
            return False

        # Convert to string for pathspec matching
        # Use forward slashes for consistency
        path_str = str(rel_path).replace("\\", "/")

        # Add trailing slash for directories (gitignore convention)
        if path.is_dir():
            path_str += "/"

        # Check if path matches any ignore pattern
        matched = spec.match_file(path_str)

        if matched:
            logger.info(f"Ignoring {path} (matches pattern in .dotxignore)")

        return matched

    def prune_directories(
        self, root: Path, directories: list[str], relative_to: Path
    ) -> list[str]:
        """
        Filter directories to remove ignored ones.

        Designed for use with os.walk() in top-down mode. Can be assigned back
        to the dirnames list in os.walk to prevent descending into ignored directories:

            dirnames[:] = ignore_rules.prune_directories(root, dirnames, package_root)
        """
        return [
            dirname
            for dirname in directories
            if not self.should_ignore(root / dirname, relative_to)
        ]
