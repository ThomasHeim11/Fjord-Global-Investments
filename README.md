# FGI Subsidiary Management

## What the application does

```
   Your three data sources                          Three ways to use it
   -----------------------                          --------------------

   register.csv   (100 entities) --+            +-->  REVIEW    ranked governance issues
   board_updates.json  (~30)       +-- ingest --+-->  REGISTER  the register, searchable
   3 agent letters     (PDF)     --+            +-->  ASK       answers, with sources
```

**Review** is the heart of the tool. One click, and the AI reads all three
sources and lists every governance issue it found, each ranked Act now /
Review soon / For awareness, with a plain explanation and a recommended
action. Where two sources disagree it shows both side by side: "Per the agent
letter: 2026-06-19. Per our register: 2028-01-10."

**Register** is the subsidiary register, finally searchable: all 100 entities
in a table you can filter and sort, colour-coded by status. Click any entity
for its full record, who owns it, what it owns, and any issues found on it.

**Ask** answers natural-language questions with sources cited, for example
"Which Singapore entities have open compliance issues?" or "Which board
mandates expire in the next 60 days?"

## How it works

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
