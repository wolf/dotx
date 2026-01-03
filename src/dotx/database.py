"""
Database module for tracking dotfile installations.

Uses SQLite (local embedded database) to track which packages have installed
which files, enabling better uninstall, verification, and package management.

Exported classes:
    InstallationDB
    NoOpDB
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


class NoOpDB:
    """
    Null object implementation of database interface.

    Does nothing but provides the same interface as InstallationDB.
    Used when database tracking is disabled or not available.
    """

    def __enter__(self):
        """Context manager entry - does nothing."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - does nothing."""
        return False

    def record_installation(self, package_name: Path, target_path: Path, link_type: str):
        """No-op: does not record installation."""
        pass

    def remove_installation(self, target_path: Path):
        """No-op: does not remove installation."""
        pass

    def get_installations(self, package_name: Path) -> list[dict]:
        """No-op: returns empty list."""
        return []

    def get_all_packages(self) -> list[dict]:
        """No-op: returns empty list."""
        return []

    def verify_installations(self, package_name: Path) -> list[dict]:
        """No-op: returns empty list."""
        return []

    def get_orphaned_entries(self, package_name: Path) -> list[dict]:
        """No-op: returns empty list."""
        return []

    def clean_orphaned_entries(self, package_name: Path) -> int:
        """No-op: returns 0."""
        return 0

    def package_exists(self, package_name: Path) -> bool:
        """No-op: returns False."""
        return False


class InstallationDB:
    """
    Manages installation tracking database using SQLite.

    Tracks which source packages have installed which files/directories
    in the target directory. Supports context manager protocol for
    automatic transaction management.

    Database location: ~/.config/dotx/installed.db

    Schema:
        installations: Records of installed files/directories
        metadata: Key-value store for database metadata
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to database file. Defaults to $XDG_CONFIG_HOME/dotx/installed.db
                     (or ~/.config/dotx/installed.db if XDG_CONFIG_HOME is not set)
        """
        if db_path is None:
            # Respect XDG Base Directory specification
            config_home = os.environ.get("XDG_CONFIG_HOME")
            if config_home:
                config_dir = Path(config_home)
            else:
                config_dir = Path.home() / ".config"
            db_path = config_dir / "dotx" / "installed.db"

        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        """
        Context manager entry: open database connection and initialize schema.
        """
        # Ensure config directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path))
        # Use Row factory for dict-like access to columns by name
        self.conn.row_factory = sqlite3.Row
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Initialize schema if needed
        self._ensure_schema()

        logger.debug(f"Opened database at {self.db_path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: commit and close database connection.

        Commits transaction if no exception, rolls back otherwise.
        """
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
            logger.debug(f"Closed database at {self.db_path}")

        return False  # Don't suppress exceptions

    def _ensure_schema(self):
        """
        Create database schema if it doesn't exist.

        Loads schema from installed-schema.sql file.
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        # Load schema from SQL file
        schema_path = Path(__file__).parent / "installed-schema.sql"
        schema_sql = schema_path.read_text()

        # Execute schema using executescript (handles multiple statements)
        self.conn.executescript(schema_sql)
        self.conn.commit()

        logger.debug("Database schema initialized")

    def record_installation(
        self, package_name: Path, target_path: Path, link_type: str
    ):
        """
        Record an installation in the database.

        Args:
            package_name: Absolute path to source package
            target_path: Absolute path to installed file/directory
            link_type: Type of installation ('file', 'directory', 'created_dir')
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        package_str = str(package_name.resolve())
        target_str = str(target_path.resolve())

        try:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO installations
                (package_name, target_path, link_type, installed_at)
                VALUES (:package, :target, :link_type, :installed_at)
                """,
                {
                    "package": package_str,
                    "target": target_str,
                    "link_type": link_type,
                    "installed_at": datetime.now().isoformat(),
                },
            )
            logger.debug(f"Recorded installation: {target_str} from {package_str}")
        except Exception as e:
            logger.error(f"Failed to record installation: {e}")
            raise

    def remove_installation(self, target_path: Path):
        """
        Remove an installation record from the database.

        Args:
            target_path: Absolute path to installed file/directory
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        target_str = str(target_path.resolve())

        try:
            self.conn.execute(
                "DELETE FROM installations WHERE target_path = :target",
                {"target": target_str},
            )
            logger.debug(f"Removed installation record: {target_str}")
        except Exception as e:
            logger.error(f"Failed to remove installation: {e}")
            raise

    def get_installations(self, package_name: Path) -> list[dict]:
        """
        Get all installations for a package.

        Args:
            package_name: Absolute path to source package

        Returns:
            List of installation records as dictionaries with keys:
                - id: Database ID
                - package_name: Source package path
                - target_path: Installed file path
                - link_type: Type of installation
                - installed_at: Installation timestamp
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        package_str = str(package_name.resolve())

        cursor = self.conn.execute(
            "SELECT * FROM installations WHERE package_name = :package ORDER BY target_path",
            {"package": package_str},
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_all_packages(self) -> list[dict]:
        """
        Get all packages with installation counts.

        Returns:
            List of dictionaries with keys:
                - package_name: Source package path
                - file_count: Number of files installed
                - latest_install: Most recent installation timestamp
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("""
            SELECT
                package_name,
                COUNT(*) as file_count,
                MAX(installed_at) as latest_install
            FROM installations
            GROUP BY package_name
            ORDER BY package_name
        """)

        return [dict(row) for row in cursor.fetchall()]

    def verify_installations(self, package_name: Path) -> list[dict]:
        """
        Verify installations for a package against filesystem.

        Checks if database records match actual filesystem state.

        Args:
            package_name: Absolute path to source package

        Returns:
            List of issues found, each a dict with keys:
                - target_path: Path that has an issue
                - issue: Description of the problem
                - link_type: Expected link type
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        installations = self.get_installations(package_name)
        issues = []

        for install in installations:
            target = Path(install["target_path"])
            link_type = install["link_type"]

            # Check if file exists
            if not target.exists():
                issues.append({
                    "target_path": str(target),
                    "issue": "File missing (in DB but not on filesystem)",
                    "link_type": link_type,
                })
                continue

            # Check if it's a symlink (for file and directory types)
            if link_type in ("file", "directory"):
                if not target.is_symlink():
                    issues.append({
                        "target_path": str(target),
                        "issue": "Not a symlink (should be symlink)",
                        "link_type": link_type,
                    })
            elif link_type == "created_dir":
                if not target.is_dir() or target.is_symlink():
                    issues.append({
                        "target_path": str(target),
                        "issue": "Not a regular directory (should be created dir)",
                        "link_type": link_type,
                    })

        return issues

    def get_orphaned_entries(self, package_name: Path) -> list[dict]:
        """
        Find database entries whose targets don't exist on filesystem.

        Args:
            package_name: Absolute path to source package

        Returns:
            List of orphaned installation records
        """
        installations = self.get_installations(package_name)
        orphaned = []

        for install in installations:
            target = Path(install["target_path"])
            if not target.exists():
                orphaned.append(install)

        return orphaned

    def clean_orphaned_entries(self, package_name: Path) -> int:
        """
        Remove database entries whose targets don't exist.

        Args:
            package_name: Absolute path to source package

        Returns:
            Number of entries removed
        """
        orphaned = self.get_orphaned_entries(package_name)

        for entry in orphaned:
            self.remove_installation(Path(entry["target_path"]))
            logger.info(f"Removed orphaned DB entry: {entry['target_path']}")

        return len(orphaned)

    def package_exists(self, package_name: Path) -> bool:
        """
        Check if a package has any installations recorded.

        Args:
            package_name: Absolute path to source package

        Returns:
            True if package has installations, False otherwise
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        package_str = str(package_name.resolve())

        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM installations WHERE package_name = :package",
            {"package": package_str},
        )

        row = cursor.fetchone()
        return row["count"] > 0
