# FGI Subsidiary Management

A governance tool built for the NBIM case assignment (see `case-brief.pdf`).

Fjord Global Investments has ~100 subsidiaries across 18 jurisdictions, managed
on spreadsheets and email. This application ingests that scattered, messy data,
uses AI to surface the governance risks the team cannot currently see, and
recommends a concrete action for every issue. One click replaces hours of
manual cross-checking before the board meeting.

**Stack:** React frontend, FastAPI backend, SQLite storage, **hybrid RAG**
(BM25 keyword search + FAISS vector search, fused with reciprocal rank
fusion), LLMs via Groq free-tier open models with local Ollama fallback.

---

## What the application does

**Review** — press "Run review" and the AI reads the register, the board
notifications and the agent letters, then presents every issue found: an
executive summary, urgency tiers (Act now / Review soon / For awareness), and
one card per issue with a plain explanation and a recommended action. Where
sources disagree, the card shows both sides: "Per the agent letter: 2026-06-19.
Per our register: 2028-01-10."

**Register** — the subsidiary register, searchable: filter and sort all 100
entities, click into any of them for the full record, ownership links, matched
notifications and that entity's issues.

**Ask** — natural-language questions answered with cited sources, powered by
the hybrid RAG pipeline: "Which Singapore entities have open compliance issues?"

### Examples of what it finds

- The Luxembourg agent's letter says a board mandate expires within days; the
  register says 2028, with a different board. Two systems disagree and nobody
  could see it.
- Agent letters name six entities that are not in the register at all: the
  agents administer (and bill for) entities off the books.
- An entity registered in "Noveria", which is not a real country; a register
  row with no legal name; a parent company that does not exist; three expired
  board mandates; the same resignation reported twice by two sources.

---

## How it works

```
data/ (CSV, JSON, PDFs)
   |  ingest: parsing, date normalisation, PDF text extraction
   v
SQLite + hybrid RAG indexes (FTS5 BM25 keyword + FAISS vectors, RRF fusion)
   |
   |  POST /api/digest  (the AI pipeline, all LLM passes)
   |   1. Entity resolution: messy notification names -> register, with
   |      confidence scores; unmatched names become unknown-entity findings
   |   2. Register analysis in three passes: per-entity (over precomputed
   |      date/reference annotations), cross-entity structure, notification
   |      hygiene
   |   3. Letter reconciliation: exact-lookup existence check, then field-by-
   |      field comparison against the register
   |   4. De-duplication, then one recommended action per finding plus the
   |      executive summary
   v
React frontend, styled on nbim.no's design tokens
```

### Key design decisions

- **Hybrid RAG for unstructured text.** Letters and notifications are chunked
  and indexed twice: BM25 (exact tokens like entity names and dates) and
  dense vectors (paraphrased questions). Results are fused with reciprocal
  rank fusion. Scales from 3 letters to 3,000 without redesign. The register
  stays structured and is queried with SQL — facts come from the database,
  not from similarity search.
- **The LLM is the analyst; code prepares its inputs.** Date math and
  reference checks are precomputed into annotations ("EXPIRED 8 days ago",
  "parent NOT IN REGISTER") so the model does judgment, not arithmetic.
- **Focused passes, structured outputs.** Complex prompts are decomposed into
  single-purpose passes; every response is schema-validated JSON with a
  repair retry. This is what made small free models dependable.
- **Resilient model chain.** Five free Groq models with separate daily
  budgets, falling through on rate limits or invalid JSON, ending at a local
  Ollama model with no token limits. Identical calls are cached in SQLite,
  so re-runs are instant and free.

### Assumptions (held up for discussion)

- Slash dates in `board_updates.json` are US-style MM/DD/YYYY (every slash
  date is valid that way, several only that way).
- "Today" is pinned to 2026-06-11 for reproducible expiry calculations.
- The fund operates in 18 jurisdictions; the 19th value in the data
  ("Noveria") is treated as a finding, not a fact.

---

## What you need to run it

- Python 3.11+
- Node 18+
- A free [Groq API key](https://console.groq.com)
- Optional: [Ollama](https://ollama.com) for the unlimited offline fallback

**Backend** (terminal 1):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # paste your GROQ_API_KEY into .env
uvicorn app.main:app --port 8000
```

The database and RAG indexes build automatically from `data/` on first start.

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and press **Run review**. The first run takes about
a minute; afterwards results are cached and instant.

---

## The case data

- `data/subsidiaries.csv`: the primary subsidiary register (100 entities)
- `data/board_updates.json`: ~30 board-change notifications with mismatched
  names and mixed date formats
- `data/letters/`: 3 free-text PDF letters from external service providers

The data is deliberately messy. Part of the exercise is deciding what to
trust, what to flag, and what to recommend; this README documents those
decisions.
