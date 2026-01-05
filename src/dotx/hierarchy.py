"""
Hierarchical pattern matching for configuration files.

Provides a generic system for loading and merging pattern files from multiple
sources with precedence rules, similar to how git handles .gitignore files.

Used for both .dotxignore (which files to ignore) and .always-create (which
directories must be real directories, never symlinked).

Exported classes:
    HierarchicalPatternMatcher
"""

from pathlib import Path

import pathspec
from loguru import logger


class HierarchicalPatternMatcher:
    """
    Manages hierarchical pattern files with precedence rules.

    Loads patterns from multiple sources in order of increasing precedence:
    1. Built-in defaults (shipped with dotx)
    2. User global config (~/.config/dotx/{filename})
    3. Package-local files (found while walking the tree, root to leaf)

    Later patterns override earlier ones. Supports gitignore-style patterns
    including negation with '!' prefix.
    """

    def __init__(self, filename: str):
        """
        Initialize pattern matcher for a specific filename.

        Args:
            filename: Name of pattern file to look for (e.g., ".dotxignore", ".always-create")
        """
        self.filename = filename
        self.spec: pathspec.PathSpec | None = None

    def load_patterns(
        self,
        builtin_file: Path,
        user_config: Path | None,
        package_files: list[Path],
    ) -> None:
        """
        Load and merge patterns from all sources.

        Patterns are loaded in order of increasing precedence:
        builtin → user → package files (root to leaf)

        Args:
            builtin_file: Path to built-in default patterns (shipped with dotx)
            user_config: Path to user's global config file (optional, may not exist)
            package_files: List of pattern files found in package, ordered root to leaf
        """
        all_patterns = []

        # 1. Load built-in patterns (lowest precedence)
        if builtin_file.exists():
            patterns = self._load_file(builtin_file, "built-in")
            all_patterns.extend(patterns)
            logger.debug(f"Loaded {len(patterns)} patterns from built-in {self.filename}")
        else:
            logger.warning(f"Built-in {builtin_file} not found")

        # 2. Load user global config (middle precedence)
        if user_config and user_config.exists():
            patterns = self._load_file(user_config, "user config")
            all_patterns.extend(patterns)
            logger.debug(f"Loaded {len(patterns)} patterns from user {user_config}")

        # 3. Load package-local files (highest precedence, root to leaf)
        for package_file in package_files:
            if package_file.exists():
                patterns = self._load_file(package_file, "package")
                all_patterns.extend(patterns)
                logger.debug(f"Loaded {len(patterns)} patterns from {package_file}")

        # Compile all patterns into a PathSpec
        self.spec = pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)
        logger.debug(f"Total patterns loaded for {self.filename}: {len(all_patterns)}")

    def _load_file(self, path: Path, source_type: str) -> list[str]:
        """
        Load patterns from a file.

        Args:
            path: Path to pattern file
            source_type: Description of source for logging (e.g., "built-in", "user config")

        Returns:
            List of pattern strings (comments and empty lines removed)
        """
        try:
            content = path.read_text()
            patterns = []
            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
            return patterns
        except Exception as e:
            logger.warning(f"Failed to load {source_type} patterns from {path}: {e}")
            return []

    def matches(self, path: Path | str, is_dir: bool = False) -> bool:
        """
        Check if a path matches the loaded patterns.

        Args:
            path: Path to check (can be Path object or string)
            is_dir: Whether the path is a directory (for matching directory patterns)

        Returns:
            True if path matches patterns (should be ignored/forced-create/etc)
        """
        if self.spec is None:
            logger.warning(f"Pattern matcher for {self.filename} not loaded, returning False")
            return False

        # Convert to string for pathspec matching
        path_str = str(path)

        # For directory patterns (e.g., "node_modules/"), pathspec needs
        # the path to end with "/" to match properly
        if is_dir:
            path_str = path_str + "/"

        # pathspec matches return True if the path should be included
        # For gitignore-style patterns, this means "should be ignored"
        return self.spec.match_file(path_str)
