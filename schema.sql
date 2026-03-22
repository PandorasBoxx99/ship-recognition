-- Schiffs-Scraper Database Schema

-- Scraping Jobs
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    name TEXT,
    status TEXT DEFAULT 'pending',  -- pending, running, paused, completed, failed
    total_items INTEGER DEFAULT 0,
    downloaded INTEGER DEFAULT 0,
    limit_count INTEGER,
    delay_min REAL DEFAULT 1.0,
    delay_max REAL DEFAULT 5.0,
    vpn_required BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Downloaded Items (Schiffe/Bilder)
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    image_url TEXT,
    local_path TEXT,
    ship_name TEXT,
    ship_type TEXT,
    imo_number TEXT,
    mmsi TEXT,
    metadata TEXT,  -- JSON blob for extra data
    status TEXT DEFAULT 'pending',  -- pending, downloaded, failed, skipped
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    downloaded_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Categories/Folders found on websites
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    parent_id INTEGER,
    item_count INTEGER DEFAULT 0,
    selected BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- VPN Status Log
CREATE TABLE IF NOT EXISTS vpn_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,  -- connect, disconnect, rotate
    country TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT 1
);

-- Predefined URLs for Settings
CREATE TABLE IF NOT EXISTS predefined_urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default URLs if not exists
INSERT OR IGNORE INTO predefined_urls (url, name) VALUES 
    ('https://www.shipspotting.com/', 'ShipSpotting'),
    ('https://www.vesselfinder.com/', 'VesselFinder'),
    ('https://www.marinetraffic.com/', 'MarineTraffic'),
    ('https://www.fleetmon.com/', 'FleetMon');

-- Classification Results
CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    image_path TEXT,
    predicted_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    all_predictions TEXT,  -- JSON: [{label, confidence}, ...]
    model_name TEXT DEFAULT 'vit-ship-classifier',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Augmentation Log
CREATE TABLE IF NOT EXISTS augmentation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_dir TEXT NOT NULL,
    output_dir TEXT,
    num_source_images INTEGER,
    num_generated INTEGER,
    transforms_config TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_items_job ON items(job_id);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_categories_job ON categories(job_id);
CREATE INDEX IF NOT EXISTS idx_classifications_item ON classifications(item_id);
