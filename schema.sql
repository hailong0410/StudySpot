CREATE TABLE IF NOT EXISTS study_spaces (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    study_type TEXT NOT NULL CHECK (study_type IN ('individual','group','both')),
    outlets INTEGER NOT NULL CHECK (outlets IN (0,1)),
    atmosphere TEXT NOT NULL CHECK (atmosphere IN ('quiet','moderate','lively'))
);
CREATE TABLE IF NOT EXISTS status_reports (
    id INTEGER PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES study_spaces(id),
    crowd TEXT NOT NULL CHECK (crowd IN ('low','medium','high')),
    noise TEXT NOT NULL CHECK (noise IN ('quiet','moderate','loud')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_space_time ON status_reports(space_id, created_at DESC);
