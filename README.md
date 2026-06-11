# FGI Subsidiary Management — Case Assignment Data

## Background

Fjord Global Investments (FGI) is a fictional sovereign wealth fund managing ~$800bn
across global real estate and renewable energy infrastructure. It has grown from a
handful of subsidiaries to roughly **100 entities across 18 jurisdictions** in under a
decade, largely through acquisition. The Subsidiary & Corporate Management team runs
all of this on spreadsheets and email — and a board meeting is days away.

Your job (see `case-brief.pdf` for the full assignment) is to bring order to this chaos:
ingest the messy data, surface the governance risks the team can't currently see, and
show how AI and smart tooling can give a small legal team superpowers.

## Your data

- `data/subsidiaries.csv` — Primary subsidiary register (100 entities).
- `data/board_updates.json` — Recent board-change notifications (~35 entries). Messy by
  nature: names don't always match the register, dates come in mixed formats, and some
  entries reference entities you won't find in the CSV.
- `data/letters/` — 3 PDF letters from external service providers (free text).

## Your task

See `case-brief.pdf`. In short: build a React/Angular frontend and a FastAPI backend
that uses an LLM to fetch, summarise, filter, and recommend actions over this data.

## A note on the data

The data is deliberately messy and incomplete — just like the real thing. Part of the
exercise is deciding what to trust, what to flag, and what to recommend. There may be a
few surprises in here. We're not testing whether you find every one; we're interested in
how you reason about messy, real-world governance data.

## Questions?

Make assumptions and justify them when you meet us in the interview. 
