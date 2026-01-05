-- Database schema for dotx installation tracking

-- Track installed files and directories
CREATE TABLE IF NOT EXISTS installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_root TEXT NOT NULL,              -- Base directory for packages (e.g., ~/dotfiles)
    package_name TEXT NOT NULL,              -- Semantic package name (e.g., helix)
    source_package_root TEXT NOT NULL,       -- Absolute path where files are linked from
    target_path TEXT NOT NULL UNIQUE,        -- Absolute path to installed file (must be unique)
    link_type TEXT NOT NULL,                 -- 'file', 'directory', 'created_dir'
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_package ON installations(package_root, package_name);
CREATE INDEX IF NOT EXISTS idx_source_package_root ON installations(source_package_root);
-- Note: idx_target_path is redundant with UNIQUE constraint, which creates an index

-- Metadata key-value store
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initialize schema version
INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '2');
