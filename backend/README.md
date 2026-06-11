# FGI Subsidiary Management: Backend

FastAPI backend: ingests the messy governance data, runs the AI review
pipeline, and serves the register, findings and Q&A to the frontend.
See the repository root README for the full overview.

## Architecture

```
/data (CSV, JSON, PDFs)
   |  ingest (rebuildable, idempotent)
   v
SQLite (storage/fgi.db)
   |- entities          structured register: queried with SQL, never RAG
   |- board_updates     raw + normalized dates; LLM entity resolution
   |- documents/chunks  letters + notifications, chunked for retrieval
   |- chunks_fts        BM25 keyword index (SQLite FTS5)
   |- findings/runs     review output
   |- llm_cache         cached LLM responses (instant, free re-runs)
storage/chunks.faiss    dense vector index (local sentence-transformers)
```

**Hybrid RAG** = BM25 (FTS5) + dense vectors (FAISS), fused with Reciprocal
Rank Fusion. BM25 wins on exact tokens (entity names, "S.à r.l.", dates);
embeddings win on paraphrase ("which entities have compliance problems?").
RRF combines the rankings without score calibration.

**Design principles**

- Structured data stays structured: the register is queried with SQL. Only
  unstructured text (letters, notification notes) goes through retrieval.
- The LLM is the analyst: register analysis, entity resolution, letter
  reconciliation and recommendations are all model passes, so new risk
  patterns, jurisdictions and letter formats are absorbed without code
  changes. Deterministic code prepares the model's inputs (date annotations,
  existence lookups) so the LLM does judgment, not arithmetic.
- Every LLM response is schema-validated JSON with a repair retry.
- Model resilience: five free Groq models tried in order (each has its own
  daily budget), falling through on rate limits or invalid JSON, ending at a
  local Ollama model with no token limits.
- Everything in `storage/` is derived: delete it and re-run ingest.

**Review pipeline** (`POST /api/digest`): LLM entity resolution (unmatched
notifications become unknown-entity findings) -> LLM register analysis in
three passes (per-entity, cross-entity structure, notification hygiene) ->
LLM letter reconciliation (existence check, then field-by-field comparison)
-> de-duplication -> LLM recommendation per finding + executive summary.

## Setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your GROQ_API_KEY (free at console.groq.com)
uvicorn app.main:app --port 8000   # auto-ingests ../data on first start
```

## CLI

```bash
python3 -m app.cli ingest     # rebuild DB + indexes from ../data
python3 -m app.cli digest     # run the review, print findings
python3 -m app.cli reset      # wipe derived state and re-ingest
python3 -m app.cli search "Singapore Solar III compliance"          # hybrid
python3 -m app.cli search "expiring mandates" --mode bm25           # keyword only
python3 -m app.cli search "who resigned recently" --mode vector     # semantic only
```

## Assumptions (to discuss in the interview)

- Slash dates in board_updates.json are US-style MM/DD/YYYY: every slash date
  parses validly that way, several only that way.
- "Today" is pinned to 2026-06-11 (`REFERENCE_DATE`) so expiry/overdue
  calculations are reproducible against the dataset's timeline.
- Embeddings are local (all-MiniLM-L6-v2): zero cost, offline-capable demo;
  swapping to a hosted embedding API is a one-function change.
