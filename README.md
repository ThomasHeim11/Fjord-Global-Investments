# FGI Subsidiary Management

## What the application does

**Review** is the heart of the tool. One click, and the AI reads all three
sources and lists every governance issue it found, each ranked by risk level
(High / Medium / Low), with a plain explanation and a recommended
action. Where two sources disagree it shows both side by side: "Per the agent
letter: 2026-06-19. Per our register: 2028-01-10."

**Register** is the subsidiary register, finally searchable: all 100 entities
in a table you can filter and sort, colour-coded by status. Click any entity
for its full record, who owns it, what it owns, and any issues found on it.

**Ask** answers natural-language questions with sources cited, for example
"Which Singapore entities have open compliance issues?" or "Which board
mandates expire in the next 60 days?"

## How it works

Three stages: get the messy data clean, make it searchable, then let the AI
reason over it.

```
   1. PREPARE              2. STORE & INDEX            3. USE IT (the AI)
   ----------             ----------------            ------------------

   CSV  ─┐                SQLite  the register,       REVIEW  one click runs
   JSON  ├─►  ingest ─►           queried with SQL ─► 5 LLM passes and lists
   PDFs ─┘                BM25    keyword index       every issue + a fix
                          vector  meaning index   ─► ASK     ask in plain
                                                     English, get an answer
                                                     with its sources cited
                                                            │
                                                            ▼
                                                      React frontend
```

The Review path and the Ask path read the same stored data; Review scans
everything in one pass, Ask retrieves just the passages a question needs.
That retrieval step is the hybrid RAG pipeline:

```
   How Ask finds the right text (hybrid RAG):

   your question ─┬─► BM25 search    (exact words: names, IDs, "S.à r.l.") ─┐
                  │                                                         ├─► merge ─► top passages ─► LLM answer
                  └─► vector search  (meaning: "compliance problems")      ─┘
```

The two searches catch different things, so we run both and merge the rankings
(reciprocal rank fusion). The merged passages, plus the SQL facts, are handed
to the LLM, which writes the answer and cites where each part came from.

**1. Prepare the data.** Ingest reads the three sources, extracts text from
the PDFs, and normalises the dates (the notifications mix formats, so we pin
them to one calendar). The result is one clean, queryable copy of everything.

**2. Store and index (SQLite + hybrid RAG).** The register lives in SQLite as
structured facts, queried with plain SQL. The free-text documents (letters,
notification notes) also get two search indexes: a keyword index (BM25) for
exact matches like entity names and legal suffixes, and a vector index for
meaning-based matches like "compliance problems." Searching both and merging
the results is "hybrid RAG": it finds things neither index would alone, and
it powers the Ask page.

**3. Review (the AI pipeline).** One request (`POST /api/digest`) runs the
analysis as a series of focused LLM passes:

1. **Entity resolution**: match each messy notification name to the register.
   "No match" is a valid answer; every unmatched notification becomes an
   unknown-entity finding.
2. **Register analysis** in three passes: per-entity review (mandates,
   filings, status), cross-entity structure (duplicate names, director
   concentration), and notification hygiene (duplicates, contradictions).
3. **Letter reconciliation**: check which entities each letter names exist in
   the register, then compare the rest field by field to catch disagreements.
4. **De-duplication**: collapse the same issue surfaced by two passes into one.
5. **Recommendations**: one action per finding, plus the executive summary.

The results render in the React frontend, styled on nbim.no's design tokens.

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
pip install -r ../requirements.txt   # single requirements file at the repo root
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
