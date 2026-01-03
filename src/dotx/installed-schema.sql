-- Database schema for dotx installation tracking
-- Version: 1

-- Track installed files and directories
CREATE TABLE IF NOT EXISTS installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name TEXT NOT NULL,        -- Absolute path to source package
    target_path TEXT NOT NULL,         -- Absolute path to installed file
    link_type TEXT NOT NULL,           -- 'file', 'directory', 'created_dir'
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(package_name, target_path)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_package_name ON installations(package_name);
CREATE INDEX IF NOT EXISTS idx_target_path ON installations(target_path);

-- Metadata key-value store
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initialize schema version
INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1');
