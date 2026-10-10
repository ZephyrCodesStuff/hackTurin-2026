PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS CAMERA (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
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
    timestamp INTEGER NOT NULL,
    CAMERA_id TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (CAMERA_id) REFERENCES CAMERA (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS OBJECT_DETECTED (
    id INTEGER NOT NULL,
    velocity REAL,
    timestamp INTEGER NOT NULL,
    CAMERA_id TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (CAMERA_id) REFERENCES CAMERA (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);
