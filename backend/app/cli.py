"""Developer CLI.

  python3 -m app.cli ingest                  rebuild DB + indexes from /data
  python3 -m app.cli search "query"          hybrid search
  python3 -m app.cli search "query" --mode bm25|vector|hybrid
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Rebuild database and search indexes")
    sub.add_parser("digest", help="Run the digest pipeline and print findings")
    sub.add_parser("reset", help="Wipe all derived state (DB, indexes, cache) and re-ingest")

    p_search = sub.add_parser("search", help="Query the hybrid retriever")
    p_search.add_argument("query")
    p_search.add_argument("--mode", choices=["hybrid", "bm25", "vector"], default="hybrid")
    p_search.add_argument("-k", type=int, default=5)

    args = parser.parse_args()

    if args.command == "ingest":
        from .ingest import run_ingest
        stats = run_ingest()
        for key, value in stats.items():
            print(f"{key}: {value}")

    elif args.command == "reset":
        from .config import DB_PATH, FAISS_INDEX_PATH
        from .ingest import run_ingest
        for path in (DB_PATH, FAISS_INDEX_PATH):
            path.unlink(missing_ok=True)
        stats = run_ingest()
        print("derived state wiped and rebuilt:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif args.command == "digest":
        from .analysis.digest import run_digest
        from .db import get_conn
        from .llm.client import LLMNotConfigured
        try:
            result = run_digest()
        except LLMNotConfigured as exc:
            raise SystemExit(f"Cannot run digest: {exc}")
        print(f"run {result['run_id']} [{result['status']}] — {result['stats']}\n")
        if result["summary"]:
            print(f"SUMMARY: {result['summary']}\n")
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM findings WHERE run_id = ? ORDER BY id", (result["run_id"],)
            ).fetchall()
        for r in rows:
            print(f"[{r['severity'].upper():8}] {r['category']:15} {r['title']}")
            if r["recommendation"]:
                print(f"           → {r['recommendation']}")

    elif args.command == "search":
        from .rag.retriever import search
        for r in search(args.query, k=args.k, mode=args.mode):
            preview = " ".join(r.text.split())[:160]
            print(f"[{r.score:.4f}] ({'+'.join(r.matched_by)}) {r.source_type}:{r.source_ref}")
            print(f"    {preview}\n")


if __name__ == "__main__":
    main()
