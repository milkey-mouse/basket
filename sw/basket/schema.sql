DROP TABLE IF EXISTS bluetooth;
DROP TABLE IF EXISTS singleton;

CREATE TABLE bluetooth (
    macaddr TEXT UNIQUE NOT NULL,
    name TEXT
);

CREATE TABLE singleton (
    idx INTEGER NOT NULL UNIQUE
      DEFAULT 1 CHECK (idx = 1),
    passwordHash TEXT NOT NULL
);
