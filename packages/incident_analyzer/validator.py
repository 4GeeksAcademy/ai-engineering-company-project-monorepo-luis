"""Validation rules for Nexova incident records."""

import re
from typing import Dict, List, Optional, Tuple
from .models import (
    VALID_CATEGORIES,
    VALID_STATUSES,
    RULE_LABELS,
    RowError,
)

REQUIRED_COLUMNS = [
    "ticket_id",
    "date",
    "client_company",
    "category",
    "description",
    "agent_id",
    "status",
    "customer_email",
    "satisfaction_score",
]

_AGENT_ID_REGEX = re.compile(r"^AGT-\d{2}$")
_TICKET_ID_REGEX = re.compile(r"^NXV-[A-Za-z0-9]{6}$")
_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_row(
    row: Dict[str, str],
    row_number: int,
) -> Tuple[bool, List[RowError], Optional[int]]:
    """
    Validates a single row against business rules.
    
    Returns:
        (is_valid, list_of_errors, parsed_satisfaction_score)
        
    CRITICAL: Never include raw field values (especially customer_email)
    in the RowError message.
    """
    errors: List[RowError] = []

    # 1. client_company
    company = row.get("client_company", "").strip()
    if not company:
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="missing_client_company",
                message="Missing client_company",
            )
        )

    # 2. category
    category = row.get("category", "").strip()
    if not category or category not in VALID_CATEGORIES:
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_category",
                message="Invalid or missing category",
            )
        )

    # 3. description
    description = row.get("description", "").strip()
    if len(description) < 5:
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_description",
                message="Invalid or missing description (minimum 5 characters)",
            )
        )

    # 4. agent_id
    agent_id = row.get("agent_id", "").strip()
    if not agent_id or not _AGENT_ID_REGEX.match(agent_id):
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_agent_id",
                message="Invalid or missing agent_id (expected format AGT-XX)",
            )
        )

    # 5. customer_email (PII - NEVER log or return email string)
    email = row.get("customer_email", "").strip()
    if not email or "@" not in email:
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_email",
                message="Invalid or missing email",
            )
        )

    # 6. status
    status = row.get("status", "").strip()
    if not status or status not in VALID_STATUSES:
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_status",
                message="Invalid or missing status (expected OPEN, CLOSED, or DISCARDED)",
            )
        )

    # 7. ticket_id
    ticket_id = row.get("ticket_id", "").strip()
    if not ticket_id or not _TICKET_ID_REGEX.match(ticket_id):
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_ticket_id",
                message="Invalid or missing ticket_id (expected format NXV-XXXXXX)",
            )
        )

    # 8. date
    date_val = row.get("date", "").strip()
    if not date_val or not _DATE_REGEX.match(date_val):
        errors.append(
            RowError(
                row_number=row_number,
                rule_key="invalid_or_missing_date",
                message="Invalid or missing date (expected format YYYY-MM-DD)",
            )
        )

    # 9. satisfaction_score
    score_raw = row.get("satisfaction_score", "").strip()
    parsed_score: Optional[int] = None

    if status == "CLOSED":
        if not score_raw:
            errors.append(
                RowError(
                    row_number=row_number,
                    rule_key="closed_no_score",
                    message="Closed ticket, no score",
                )
            )
        else:
            try:
                val = int(score_raw)
                if 1 <= val <= 5:
                    parsed_score = val
                else:
                    errors.append(
                        RowError(
                            row_number=row_number,
                            rule_key="invalid_score",
                            message="Invalid satisfaction score (must be integer 1-5)",
                        )
                    )
            except ValueError:
                errors.append(
                    RowError(
                        row_number=row_number,
                        rule_key="invalid_score",
                        message="Invalid satisfaction score (must be integer 1-5)",
                    )
                )
    else:
        # OPEN or DISCARDED: score is optional, but if present must be 1..5
        if score_raw:
            try:
                val = int(score_raw)
                if 1 <= val <= 5:
                    parsed_score = val
                else:
                    errors.append(
                        RowError(
                            row_number=row_number,
                            rule_key="invalid_score",
                            message="Invalid satisfaction score (must be integer 1-5)",
                        )
                    )
            except ValueError:
                errors.append(
                    RowError(
                        row_number=row_number,
                        rule_key="invalid_score",
                        message="Invalid satisfaction score (must be integer 1-5)",
                    )
                )

    is_valid = len(errors) == 0
    return is_valid, errors, parsed_score
