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

    def __init__(self, db_path: Path | None = None):
        """
        Initialize database connection.

        Uses XDG_CONFIG_HOME/dotx/installed.db if db_path is not provided
        (or ~/.config/dotx/installed.db if XDG_CONFIG_HOME is not set).
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
        self.conn: sqlite3.Connection | None = None

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

        Commits transaction on success, rolls back on exception.
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

        Loads and executes schema from installed-schema.sql file.
        Handles migration from old schema versions.
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        # Check if this is an existing database with old schema
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='installations'"
        )
        existing_table = cursor.fetchone()

        if existing_table:
            # Check schema version
            try:
                cursor = self.conn.execute(
                    "SELECT value FROM metadata WHERE key='schema_version'"
                )
                version_row = cursor.fetchone()
                if version_row and version_row[0] == '1':
                    # Old schema - need to migrate
                    logger.warning("Detected old database schema (v1). Migrating to v2...")
                    self._migrate_schema_v1_to_v2()
                    return
            except Exception:
                # metadata table might not exist in very old versions
                pass

        # Load schema from SQL file
        schema_path = Path(__file__).parent / "installed-schema.sql"
        schema_sql = schema_path.read_text()

        # Execute schema using executescript (handles multiple statements)
        self.conn.executescript(schema_sql)
        self.conn.commit()

        logger.debug("Database schema initialized")

    def _migrate_schema_v1_to_v2(self):
        """
        Migrate database from schema v1 to v2.

        v1: UNIQUE(package_name, target_path)
        v2: UNIQUE(target_path)

        Strategy: Recreate table with new schema, keeping most recent entry per target_path.
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        logger.info("Migrating database schema from v1 to v2")

        # Create temporary table with new schema
        self.conn.execute("""
            CREATE TABLE installations_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL,
                target_path TEXT NOT NULL UNIQUE,
                link_type TEXT NOT NULL,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Copy data, keeping only the most recent entry for each target_path
        # (in case multiple packages claimed the same target)
        self.conn.execute("""
            INSERT INTO installations_new (package_name, target_path, link_type, installed_at)
            SELECT package_name, target_path, link_type, installed_at
            FROM installations
            WHERE id IN (
                SELECT MAX(id)
                FROM installations
                GROUP BY target_path
            )
        """)

        # Drop old table and rename new one
        self.conn.execute("DROP TABLE installations")
        self.conn.execute("ALTER TABLE installations_new RENAME TO installations")

        # Recreate indexes
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_package_name ON installations(package_name)"
        )

        # Update schema version
        self.conn.execute(
            "UPDATE metadata SET value = '2' WHERE key = 'schema_version'"
        )

        self.conn.commit()
        logger.info("Database migration completed successfully")

    def record_installation(
        self, package_name: Path, target_path: Path, link_type: str
    ):
        """
        Record an installation in the database.

        The link_type should be 'file', 'directory', or 'created_dir'.
        Both paths are resolved to absolute paths before storage.
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

        Path is resolved to absolute path before lookup.
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
        Get all installations for a package, ordered by target path.

        Each installation record is a dict with keys: id, package_name,
        target_path, link_type, and installed_at.
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
        Get all packages with installation counts, ordered by package name.

        Each package record is a dict with keys: package_name, file_count,
        and latest_install timestamp.
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

        Checks if database records match actual filesystem state. Each issue
        is a dict with keys: target_path, issue (description), and link_type.
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

        Returns orphaned installation records (target files/directories are missing).
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
        Remove database entries whose targets don't exist on filesystem.

        Logs each removed entry and returns count of entries removed.
        """
        orphaned = self.get_orphaned_entries(package_name)

        for entry in orphaned:
            self.remove_installation(Path(entry["target_path"]))
            logger.info(f"Removed orphaned DB entry: {entry['target_path']}")

        return len(orphaned)

    def package_exists(self, package_name: Path) -> bool:
        """
        Check if a package has any installations recorded in the database.
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
