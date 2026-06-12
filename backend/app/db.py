"""SQLite access layer.

One file-based database holds the normalized register, board updates, document
chunks and the FTS5 (BM25) keyword index. Everything is rebuilt from the
source data in /data, so the database itself is disposable.
"""
import sqlite3

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id            TEXT PRIMARY KEY,
    entity_name          TEXT,
    entity_type          TEXT,
    jurisdiction         TEXT,
    incorporation_date   TEXT,
    parent_entity_id     TEXT,
    ownership_pct        REAL,
    registered_address   TEXT,
    board_members        TEXT,
    board_mandate_expiry TEXT,
    annual_filing_due    TEXT,
    annual_filing_status TEXT,
    registered_agent     TEXT,
    status               TEXT,
    asset_class          TEXT,
    asset_description    TEXT
);

CREATE TABLE IF NOT EXISTS board_updates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_raw        TEXT,
    date_iso        TEXT,           -- normalized; NULL if unparseable
    entity_name_raw TEXT,
    change_type     TEXT,
    details         TEXT,
    source          TEXT,
    resolved_entity_id TEXT,        -- filled in by LLM entity resolution (phase 2)
    resolution_confidence REAL,
    resolution_note TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT UNIQUE,
    title       TEXT,
    source_type TEXT,               -- 'letter' | 'uploaded'
    full_text   TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    source_type TEXT,               -- 'letter' | 'board_update' | 'uploaded'
    source_ref  TEXT,               -- filename or board_update id, for citations
    chunk_index INTEGER,
    text        TEXT
);

-- BM25 keyword index. FTS5 ranks MATCH results with the BM25 algorithm.
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);

-- LLM response cache: repeated digest runs are instant and free.
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key  TEXT PRIMARY KEY,
    response   TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS digest_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (datetime('now')),
    status     TEXT,                -- 'completed' | 'failed'
    summary    TEXT,                -- LLM executive summary
    model      TEXT,
    stats_json TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER REFERENCES digest_runs(id),
    category       TEXT,            -- data_integrity | mandate | filing | status | governance | conflict | unknown_entity
    severity       TEXT,            -- critical | warning | info
    entity_id      TEXT,            -- register entity if applicable
    entity_name    TEXT,
    title          TEXT,
    description    TEXT,
    evidence_json  TEXT,            -- which sources say what
    recommendation TEXT,            -- LLM-generated action
    detected_by    TEXT             -- 'rule:<name>' | 'llm:reconciliation' | 'llm:resolution'
);

-- PortfolioGPT chat history, persisted server-side so conversations survive a
-- page reload and are ready to scope per-user once auth exists.
CREATE TABLE IF NOT EXISTS chat_conversations (
    id         TEXT PRIMARY KEY,    -- server-generated uuid hex
    title      TEXT,                -- first question, truncated
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role            TEXT,            -- 'user' | 'assistant'
    content         TEXT,
    sources_json    TEXT,            -- assistant only: JSON array of cited sources
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conv ON chat_messages(conversation_id, id);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
