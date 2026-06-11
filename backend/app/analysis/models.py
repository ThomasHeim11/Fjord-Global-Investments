"""Shared finding model used by every analysis step."""
from dataclasses import dataclass, field

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass
class Finding:
    category: str             # data_integrity | mandate | filing | status | governance | conflict | unknown_entity
    severity: str             # critical | warning | info
    title: str
    description: str
    detected_by: str          # 'llm:analysis' | 'llm:reconciliation' | 'llm:resolution'
    entity_id: str | None = None
    entity_name: str | None = None
    evidence: dict = field(default_factory=dict)
    recommendation: str | None = None
