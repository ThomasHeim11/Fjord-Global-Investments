# FGI Subsidiary Management — Backend

FastAPI backend for the FGI case assignment: ingests the messy governance
data, surfaces risks, and uses an LLM to summarise and recommend actions.

## Architecture

```
/data (CSV, JSON, PDFs)
   │  ingest (rebuildable, idempotent)
   ▼
SQLite (storage/fgi.db)
   ├─ entities          ← structured register: answered with SQL, never RAG
   ├─ board_updates     ← raw + normalized dates; LLM entity resolution
   ├─ documents/chunks  ← letters + updates, chunked for retrieval
   ├─ chunks_fts        ← BM25 keyword index (SQLite FTS5)
   └─ llm_cache         ← cached LLM responses (fast + cheap demos)
storage/chunks.faiss    ← dense vector index (local sentence-transformers)
```

**Hybrid retrieval** = BM25 (FTS5) + dense vectors (FAISS), fused with
Reciprocal Rank Fusion. BM25 wins on exact tokens (entity names, "S.à r.l.",
dates); embeddings win on paraphrase ("which entities have compliance
problems?"). RRF combines the rankings without score calibration.

**Design principles**
- Structured data stays structured: the register is queried with SQL.
  Only unstructured text (letters, update notes) goes through retrieval.
- LLM-first analysis (deliberate choice): the assignment is about automating
  the review a legal team does by hand today, so the LLM is the analyst —
  register analysis, entity resolution, letter reconciliation and
  recommendations are all model passes. Unlike hand-written rules, this
  generalizes: a new risk pattern next quarter doesn't require a code change,
  and the same pipeline absorbs new jurisdictions, new letter formats and
  new data sources unchanged.
- Everything in `storage/` is derived — delete it and re-run ingest.

**Digest pipeline** (`POST /api/digest`): LLM entity resolution →
unmatched-notification findings → LLM register analysis → LLM letter
reconciliation → LLM recommendation per finding + executive summary.
Requires `ANTHROPIC_API_KEY`; responses are cached in SQLite so re-runs
on unchanged data are instant and free.

## Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python3 -m app.cli ingest     # build DB + indexes from ../data
```

## CLI

```bash
python3 -m app.cli search "Singapore Solar III compliance"          # hybrid
python3 -m app.cli search "expiring mandates" --mode bm25           # keyword only
python3 -m app.cli search "who resigned recently" --mode vector     # semantic only
```

## Assumptions (to discuss in the interview)

- Slash dates in board_updates.json are US-style MM/DD/YYYY — every slash
  date parses validly under that reading and several are only valid month-first.
- "Today" is pinned to 2026-06-11 (`REFERENCE_DATE`) so expiry/overdue
  calculations are reproducible against the dataset's timeline.
- Embeddings are local (all-MiniLM-L6-v2): zero cost, offline-capable demo;
  swapping to a hosted embedding API is a one-function change.
