"""Data models and constants for Nexova incident analyzer."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

VALID_CATEGORIES = (
    "TECHNICAL",
    "BILLING",
    "ACCESS",
    "HR_QUERY",
    "COMPLAINT",
)

VALID_STATUSES = (
    "OPEN",
    "CLOSED",
    "DISCARDED",
)

# Rule keys mapped to human-readable label
RULE_LABELS: Dict[str, str] = {
    "missing_client_company": "Missing client_company",
    "invalid_or_missing_category": "Invalid or missing category",
    "invalid_or_missing_email": "Invalid or missing email",
    "closed_no_score": "Closed ticket, no score",
    "invalid_score": "Invalid satisfaction score",
    "invalid_or_missing_description": "Invalid or missing description",
    "invalid_or_missing_agent_id": "Invalid or missing agent_id",
    "invalid_or_missing_ticket_id": "Invalid or missing ticket_id",
    "invalid_or_missing_date": "Invalid or missing date",
    "invalid_or_missing_status": "Invalid or missing status",
}


@dataclass
class RowError:
    """Represents a validation error on a specific row, WITHOUT storing PII."""
    row_number: int
    rule_key: str
    message: str


@dataclass
class SatisfactionStats:
    """Statistics for satisfaction scores among valid CLOSED tickets."""
    scored_tickets: int = 0
    total_closed_tickets: int = 0
    average_score: Optional[float] = None
    score_distribution: Dict[int, int] = field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scored_tickets": self.scored_tickets,
            "total_closed_tickets": self.total_closed_tickets,
            "average_score": self.average_score,
            "score_distribution": self.score_distribution,
        }


@dataclass
class IncidentAnalysisResult:
    """Summary metrics of an incident analysis execution."""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    category_counts: Dict[str, int] = field(
        default_factory=lambda: {cat: 0 for cat in VALID_CATEGORIES}
    )
    status_counts: Dict[str, int] = field(
        default_factory=lambda: {st: 0 for st in VALID_STATUSES}
    )
    invalid_breakdown: Dict[str, int] = field(default_factory=dict)
    satisfaction: SatisfactionStats = field(default_factory=SatisfactionStats)
    row_errors: List[RowError] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "category_counts": self.category_counts,
            "status_counts": self.status_counts,
            "invalid_breakdown": self.invalid_breakdown,
            "satisfaction": self.satisfaction.to_dict(),
            "errors_count": len(self.row_errors),
        }
