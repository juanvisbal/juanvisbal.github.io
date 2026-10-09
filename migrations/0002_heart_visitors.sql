-- Which browser hearted which post, so it can unheart. `visitor` is a SHA-256 of a
-- random ID the browser keeps in localStorage (no personal data).
CREATE TABLE IF NOT EXISTS heart_visitors (
  path    TEXT NOT NULL,
  visitor TEXT NOT NULL,
  PRIMARY KEY (path, visitor)
);
