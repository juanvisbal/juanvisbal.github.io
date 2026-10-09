-- Open Heart counts for blog posts (functions/openheart/[[path]].js).
CREATE TABLE IF NOT EXISTS hearts (
  path  TEXT NOT NULL,
  emoji TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (path, emoji)
);

-- One heart per visitor per post per day. `key` is a SHA-256 of IP + path + day,
-- so no IP addresses are stored. Rows older than two days are deleted.
CREATE TABLE IF NOT EXISTS heart_votes (
  key TEXT PRIMARY KEY,
  day TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS heart_votes_day ON heart_votes (day);
