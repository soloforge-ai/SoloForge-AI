CREATE TABLE ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    body TEXT NOT NULL CHECK(length(trim(body)) > 0),
    source TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'CAPTURED' CHECK (
        status IN (
            'CAPTURED','TRIAGED','RESEARCHED','EVALUATED','GRADUATED',
            'PARKED','REJECTED','EXPERIMENT','VALIDATED','KILLED'
        )
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE idea_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    actor TEXT NOT NULL,
    reason TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE idea_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    note_type TEXT NOT NULL CHECK(note_type IN ('NOTE','RESEARCH','ASSUMPTION','EVIDENCE','RISK')),
    body TEXT NOT NULL CHECK(length(trim(body)) > 0),
    source_url TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE idea_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    demand INTEGER NOT NULL CHECK(demand BETWEEN 0 AND 5),
    feasibility INTEGER NOT NULL CHECK(feasibility BETWEEN 0 AND 5),
    strategic_fit INTEGER NOT NULL CHECK(strategic_fit BETWEEN 0 AND 5),
    weighted_score REAL NOT NULL CHECK(weighted_score BETWEEN 0 AND 5),
    signal TEXT NOT NULL CHECK(signal IN ('GRADUATE_CANDIDATE','PARK_OR_REVIEW','REJECT_CANDIDATE')),
    notes TEXT,
    evaluator TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_ideas_status_created ON ideas(status, created_at DESC);
CREATE INDEX idx_idea_events_idea_created ON idea_events(idea_id, created_at);
CREATE INDEX idx_idea_notes_idea_created ON idea_notes(idea_id, created_at DESC);
CREATE INDEX idx_idea_evaluations_idea_created ON idea_evaluations(idea_id, created_at DESC);

CREATE TRIGGER guard_idea_status_transition
BEFORE UPDATE OF status ON ideas
FOR EACH ROW
WHEN NEW.status <> OLD.status AND NOT (
       (OLD.status = 'CAPTURED' AND NEW.status IN ('TRIAGED','PARKED','REJECTED'))
    OR (OLD.status = 'TRIAGED' AND NEW.status IN ('RESEARCHED','EVALUATED','PARKED','REJECTED'))
    OR (OLD.status = 'RESEARCHED' AND NEW.status IN ('EVALUATED','PARKED','REJECTED'))
    OR (OLD.status = 'EVALUATED' AND NEW.status IN ('GRADUATED','PARKED','REJECTED'))
    OR (OLD.status = 'GRADUATED' AND NEW.status IN ('EXPERIMENT','PARKED','KILLED'))
    OR (OLD.status = 'PARKED' AND NEW.status IN ('TRIAGED','RESEARCHED','REJECTED'))
    OR (OLD.status = 'EXPERIMENT' AND NEW.status IN ('VALIDATED','KILLED','PARKED'))
)
BEGIN
    SELECT RAISE(ABORT, 'invalid idea status transition');
END;
