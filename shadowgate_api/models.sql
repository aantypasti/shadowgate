-- Users table for Shadowgate
CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT DEFAULT 'user',
  ingame_username TEXT,
  company_code  TEXT,
  fio_apikey    TEXT,
  bases         INTEGER DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
