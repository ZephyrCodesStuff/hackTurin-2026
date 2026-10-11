PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS CAMERA (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    state TEXT NOT NULL DEFAULT 'online' CHECK (state IN ('online', 'maintenance', 'offline')),
    last_heartbeat INTEGER,
    last_event_timestamp INTEGER,
    battery_level REAL,
    firmware_version TEXT,
    wifi_signal INTEGER,
    CHECK (
        length(id) = 36
        AND substr(id, 9, 1) = '-'
        AND substr(id, 14, 1) = '-'
        AND substr(id, 15, 1) = '4'
        AND substr(id, 19, 1) = '-'
        AND lower(substr(id, 20, 1)) IN ('8', '9', 'a', 'b')
        AND substr(id, 24, 1) = '-'
    )
);

CREATE TABLE IF NOT EXISTS CRASH (
    id INTEGER NOT NULL,
    photo_id TEXT NOT NULL,
    -- SQLite INTEGER is signed 64-bit, sufficient for Unix epoch milliseconds.
    timestamp INTEGER NOT NULL,
    CAMERA_id TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolved_at INTEGER,
    resolved_by TEXT,
    dispatched_units TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY (CAMERA_id) REFERENCES CAMERA (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CHECK (
        length(photo_id) = 36
        AND substr(photo_id, 9, 1) = '-'
        AND substr(photo_id, 14, 1) = '-'
        AND substr(photo_id, 15, 1) = '4'
        AND substr(photo_id, 19, 1) = '-'
        AND lower(substr(photo_id, 20, 1)) IN ('8', '9', 'a', 'b')
        AND substr(photo_id, 24, 1) = '-'
    )
);

CREATE TABLE IF NOT EXISTS LIGHT_CHANGE (
    id INTEGER NOT NULL,
    color TEXT NOT NULL CHECK (color IN ('red', 'amber', 'green')),
    timestamp INTEGER NOT NULL,
    CAMERA_id TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (CAMERA_id) REFERENCES CAMERA (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS ILLEGAL_CROSSING (
    id INTEGER NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('pedestrian', 'car', 'motorbike', 'bike', 'truck', 'animal')),
    timestamp INTEGER NOT NULL,
    CAMERA_id TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (CAMERA_id) REFERENCES CAMERA (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS OBJECT_DETECTED (
    id INTEGER NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('pedestrian', 'car', 'motorbike', 'bike', 'truck', 'animal')),
    velocity REAL,
    timestamp INTEGER NOT NULL,
    CAMERA_id TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (CAMERA_id) REFERENCES CAMERA (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS USER (
    id TEXT NOT NULL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS USER_CAMERA (
    user_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, camera_id),
    FOREIGN KEY (user_id) REFERENCES USER (id) ON DELETE CASCADE,
    FOREIGN KEY (camera_id) REFERENCES CAMERA (id) ON DELETE CASCADE
);
