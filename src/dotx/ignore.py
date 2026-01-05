"""
This module provides gitignore-style ignore rules using .dotxignore files.

Uses hierarchical pattern matching with support for:
- Built-in default ignores (shipped with dotx)
- Global ignore file at ~/.config/dotx/dotxignore
- Nested .dotxignore files (like .gitignore, hierarchical)
- Negation patterns (e.g., !important.conf)
- Comments (lines starting with #)

Exported class:
    IgnoreRules
"""

import os
from pathlib import Path

from loguru import logger

from dotx.hierarchy import HierarchicalPatternMatcher


class IgnoreRules:
    """
    Manages hierarchical .dotxignore files with gitignore-style patterns.

    Uses HierarchicalPatternMatcher to combine patterns from multiple sources:
    1. Built-in defaults (shipped with dotx)
    2. Global ignore file at ~/.config/dotx/dotxignore
    3. .dotxignore files in package (hierarchical, closest has highest precedence)

    Attributes:
        source_root: Root directory being processed
        matcher: HierarchicalPatternMatcher instance
    """

    def __init__(self, source_root: Path):
        """
        Initialize IgnoreRules for a source package.

        Args:
            source_root: Root directory of the package being processed
        """
        self.source_root = source_root
        self.matcher = HierarchicalPatternMatcher(".dotxignore")

        # Find all .dotxignore files in the package (hierarchical)
        package_files = self._find_dotxignore_files(source_root)

        # Load patterns from all sources
        builtin_file = Path(__file__).parent / "dotxignore"
        config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        user_config = Path(config_home) / "dotx" / "dotxignore"

        self.matcher.load_patterns(
            builtin_file=builtin_file,
            user_config=user_config,
            package_files=package_files,
        )

    def _find_dotxignore_files(self, root: Path) -> list[Path]:
        """
        Find all .dotxignore files in the package directory tree.

        Returns files in order from root to leaf (for proper precedence).

        Args:
            root: Root directory to search

        Returns:
            List of .dotxignore file paths, ordered root to leaf
        """
        ignore_files = []

        for dirpath, dirnames, filenames in os.walk(root):
            if ".dotxignore" in filenames:
                ignore_file = Path(dirpath) / ".dotxignore"
                ignore_files.append(ignore_file)

        # Sort by depth (root to leaf)
        ignore_files.sort(key=lambda p: len(p.relative_to(root).parts))

        return ignore_files

    def should_ignore(self, path: Path) -> bool:
        """
        Test if a path should be ignored.

        Checks the path against all applicable ignore rules considering
        precedence: built-in → user config → package files (root to leaf).

        Args:
            path: Path to check (can be absolute or relative to source_root)

        Returns:
            True if path should be ignored
        """
        # Check if path is a directory (before relativizing, while we can still check)
        is_directory = path.exists() and path.is_dir()

        # Make path relative to source_root for matching
        try:
            if path.is_absolute():
                rel_path = path.relative_to(self.source_root)
            else:
                rel_path = path
        except ValueError:
            # Path is not under source_root
            logger.warning(f"Path {path} is not under source root {self.source_root}")
            return False

        # Check with matcher
        matched = self.matcher.matches(rel_path, is_dir=is_directory)

        if matched:
            logger.debug(f"Ignoring {rel_path} (matches .dotxignore pattern)")

        return matched

    def prune_directories(
        self, root: Path, directories: list[str]
    ) -> list[str]:
        """
        Filter directories to remove ignored ones.

        Designed for use with os.walk() in top-down mode.

        Can be assigned back to the dirnames list in os.walk to prevent
        descending into ignored directories:

            dirnames[:] = ignore_rules.prune_directories(root, dirnames)

        Args:
            root: Current directory being walked
            directories: List of subdirectory names in root

        Returns:
            Filtered list of directory names (non-ignored)
        """
        return [
            dirname
            for dirname in directories
            if not self.should_ignore(root / dirname)
        ]
