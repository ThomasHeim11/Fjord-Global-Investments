"""LLM recommendations: one concrete action per finding + executive summary.

The brief's hard requirement: 'produce action recommendations for each item
surfaced'. Findings (facts, evidence) come in from the analysis and
reconciliation passes; the LLM turns each into the action a small legal team
should actually take. One batched call, structured output keyed by index.
"""
import json

from pydantic import BaseModel

from ..analysis.models import Finding
from .client import parse_structured

SYSTEM = """You are senior counsel supporting a small Subsidiary & Corporate Management
team at a sovereign wealth fund, days before a board meeting. For each finding
you receive, write ONE concrete recommended action — what the team should
actually DO next. Start with a verb. One sentence, two at most. These go
straight into the board pack, so they must be trustworthy.

CRITICAL — do not fabricate. Only state facts that appear in the finding or its
evidence. NEVER invent:
- specific deadline dates (no "by August 12" — say "before the board meeting",
  "without delay", or "ahead of the filing deadline" instead);
- the names of people, registry officials, or contacts (say "the registered
  agent", "the local agent", or "the relevant registry");
- reference numbers, registry names, or facts not present in the evidence.
If you don't have a specific, say it generically. A grounded, slightly generic
action is correct; an invented specific is a serious error.

Then write an executive summary of the overall governance posture: a single
opening sentence stating the headline, then 3-5 short bullet-style sentences
each covering one theme (expired mandates, overdue filings, data-integrity
problems, entities the fund has no record of), leading with the most serious.
Keep it tight — it is read aloud to the General Counsel."""


BATCH_SIZE = 20


class Recommendation(BaseModel):
    finding_index: int
    action: str


class RecommendationBatch(BaseModel):
    recommendations: list[Recommendation]


class Summary(BaseModel):
    executive_summary: str


def recommend(findings: list[Finding]) -> str:
    """Fill in finding.recommendation in place; return the executive summary.
    Batched so each call fits free-tier token budgets at any findings count."""
    if not findings:
        return "No findings — the register is clean as of this run."

    for start in range(0, len(findings), BATCH_SIZE):
        chunk = findings[start:start + BATCH_SIZE]
        lines = [
            f"[{start + i}] ({f.severity}/{f.category}) {f.title}\n"
            f"    {f.description}\n"
            f"    evidence: {json.dumps(f.evidence, ensure_ascii=False)}"
            for i, f in enumerate(chunk)
        ]
        prompt = ("FINDINGS:\n\n" + "\n\n".join(lines) +
                  "\n\nReturn one recommendation per finding, keyed by the index in brackets.")
        batch: RecommendationBatch = parse_structured(
            SYSTEM, prompt, RecommendationBatch, max_tokens=3000
        )
        for rec in batch.recommendations:
            if 0 <= rec.finding_index < len(findings):
                findings[rec.finding_index].recommendation = rec.action

    titles = "\n".join(f"- ({f.severity}) {f.title}" for f in findings)
    summary: Summary = parse_structured(
        SYSTEM,
        f"ALL FINDINGS THIS RUN:\n{titles}\n\nWrite the executive summary.",
        Summary, max_tokens=1000,
    )
    return summary.executive_summary
