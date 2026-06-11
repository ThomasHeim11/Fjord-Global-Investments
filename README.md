# FGI Subsidiary Management

## What the application does

The app has three pages:

**Review** is the heart of the tool. Press "Run review" and the AI reads the
subsidiary register, the board-change notifications and the agent letters,
then presents every governance issue it found: a summary written for the
General Counsel, urgency counters (Act now / Review soon / For awareness),
and one card per issue with a plain explanation and a recommended action.
Where two sources disagree, the card shows both side by side:
"Per the agent letter: 2026-06-19. Per our register: 2028-01-10."

**Register** is the subsidiary register itself, finally searchable: all 100
entities in a table you can filter and sort, with colour-coded status. Click
any entity to see its full record, who owns it, what it owns, the
notifications matched to it, and any issues found on it. This is the page for
the daily question "tell me about entity X."

**Ask** answers natural-language questions, with sources cited:
"Which Singapore entities have open compliance issues?" or
"Which board mandates expire in the next 60 days?"

## For the technically curious: how it works

```
data/ (CSV, JSON, PDFs)
   |  ingest: parsing, date normalisation, PDF text extraction
   v
SQLite  +  FTS5 keyword index (BM25)  +  FAISS vector index (local embeddings)
   |
   |  POST /api/digest  (the AI pipeline, all LLM passes)
   |    1. Entity resolution: match messy notification names to the register,
   |       with confidence scores. "No match" is a valid answer, and every
   |       unmatched notification becomes an unknown-entity finding.
   |    2. Register analysis, three focused passes:
   |       a. per-entity review in batches (mandates, filings, status,
   |          record quality), over precomputed date/reference annotations
   |       b. cross-entity structure (duplicate names, director
   |          concentration, ownership patterns)
   |       c. notification hygiene (duplicates, contradictions, updates
   |          that make no sense for the entity's status)
   |    3. Letter reconciliation: an exact-lookup cross-check splits the
   |       entities each letter names into present/absent, then the LLM
   |       writes findings for unknown entities and compares the rest
   |       field by field against the register.
   |    4. De-duplication: the same issue surfaced by two passes is collapsed
   |       to one finding.
   |    5. Recommendations: one action per finding, plus the executive summary.
   v
React frontend (Vite + TypeScript), styled on nbim.no's design tokens
```

**Stack:** FastAPI + SQLite on the backend, React on the frontend, LLMs via
Groq (free-tier open models) with local Ollama as fallback and Anthropic as a
config option.

### Design decisions worth knowing

- **The LLM is the analyst.** Every finding comes from a model pass, so a new
  risk pattern, jurisdiction or letter format next quarter requires no code
  change. Deterministic code only _prepares_ the model's inputs.
- **The model never does arithmetic.** Date math and reference checks are
  precomputed into the data the model reads: "mandate_expiry=2026-06-03
  (EXPIRED 8 days ago)", "parent=FGI-099X (NOT IN REGISTER)". The LLM spends
  its judgment where judgment is needed. This single change took expired
  mandate detection from unreliable to exact.
- **Complex prompts are decomposed into single-purpose passes.** One prompt
  doing existence-checking, value comparison and formatting at once was
  unreliable on small open models. Split into focused passes, each is hard to
  get wrong. This is how a free 17B model became dependable.
- **Structured outputs everywhere.** Every LLM response is JSON validated
  against a typed schema (with one repair retry), so malformed output cannot
  reach the UI.
- **Model fallback chain.** Each free Groq model has its own daily token
  budget. When one is exhausted or returns invalid JSON, the client falls
  through to the next, and finally to a local Ollama model with no token
  limits. A review completes as long as any backend works, even offline.
- **Caching.** Identical LLM calls are cached in SQLite, so re-running a
  review on unchanged data is instant and free.
- **Structured data stays structured.** The register is queried with SQL.
  Only unstructured text (letters, notification notes) goes through hybrid
  retrieval (BM25 + vectors, fused with reciprocal rank fusion), which powers
  the Ask page and scales from 3 letters to 3,000 without redesign.
- **SQLite + local files** because the whole thing must run on a laptop in
  the interview; the same access layer would point at Postgres for a team.

### Assumptions made (and held up for discussion)

- Slash dates in `board_updates.json` are read as US-style MM/DD/YYYY. Every
  slash date in the data is valid under that reading, several only that way.
- "Today" is pinned to 2026-06-11 so expiry and overdue calculations are
  reproducible against the dataset's timeline.
- The fund operates in 18 jurisdictions per the brief. The register contains
  a 19th value ("Noveria"), which the pipeline treats as a finding, not a fact.

---

## Running it locally

Prerequisites: Python 3.11+, Node 18+, and a free [Groq API key](https://console.groq.com).
Optional: [Ollama](https://ollama.com) running locally for the unlimited offline fallback.

**Backend** (terminal 1):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # paste your GROQ_API_KEY into .env
uvicorn app.main:app --port 8000
```

The database and search indexes build automatically from `data/` on first start.

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and press **Run review**. The first run takes about
a minute; after that, results are cached and instant.

CLI alternative for the backend pipeline:

```bash
cd backend
python3 -m app.cli ingest     # rebuild database + indexes from data/
python3 -m app.cli digest     # run the review, print findings
python3 -m app.cli reset      # wipe derived state and re-ingest
```

---

## The original case data

- `data/subsidiaries.csv`: the primary subsidiary register (100 entities)
- `data/board_updates.json`: ~30 board-change notifications. Messy by nature:
  names do not always match the register, dates come in mixed formats, some
  entries reference entities not in the CSV
- `data/letters/`: 3 free-text PDF letters from external service providers

The data is deliberately messy and incomplete. Part of the exercise is
deciding what to trust, what to flag, and what to recommend; this README and
the code comments document those decisions.
