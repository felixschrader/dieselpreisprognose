-- Anonyme Besucherstatistik (Dashboard)
-- Einmal in PostgreSQL ausführen, falls nicht per Code angelegt.

CREATE TABLE IF NOT EXISTS visitor_events (
    id UUID PRIMARY KEY,
    ts_utc TIMESTAMPTZ NOT NULL,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tab_name TEXT,
    meta JSONB
);

CREATE INDEX IF NOT EXISTS idx_visitor_events_ts ON visitor_events (ts_utc);
CREATE INDEX IF NOT EXISTS idx_visitor_events_session ON visitor_events (session_id);
