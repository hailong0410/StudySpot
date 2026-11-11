CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    space_id INTEGER NOT NULL,
    crowd TEXT NOT NULL CHECK (crowd IN ('low', 'medium', 'high')),
    noise TEXT NOT NULL CHECK (noise IN ('quiet', 'moderate', 'loud')),
    created_at INTEGER NOT NULL,
    source_key TEXT
);
--> statement-breakpoint
CREATE INDEX observations_recent ON observations (space_id, created_at DESC, id DESC);
--> statement-breakpoint
CREATE INDEX observations_source ON observations (space_id, source_key, created_at)
WHERE source_key IS NOT NULL;
--> statement-breakpoint
CREATE INDEX observations_expiry ON observations (created_at);
