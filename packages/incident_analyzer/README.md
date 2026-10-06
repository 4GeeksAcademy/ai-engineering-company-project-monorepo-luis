# `incident_analyzer` package

Internal reusable library for analyzing Nexova incident helpdesk CSV exports.

## Key Features
- **Deterministic streaming analyzer**: Process files line-by-line without high memory overhead.
- **Privacy-safe (Zero PII leakage)**: Validates `customer_email` without ever exposing, printing, or logging customer email strings.
- **Strict validation rules**: Validates mandatory schemas, categories, status, agents, and closed ticket satisfaction scores.
- **Shared across consumers**: Used directly by the CLI (`scripts/analyze.py`) and the Backoffice API (`services/api`).

## Usage Example

```python
from packages.incident_analyzer import analyze_incidents_file, export_results_to_csv_string

result = analyze_incidents_file("data/raw/incidents-nexova.csv")

print(f"Total: {result.total_records}")
print(f"Valid: {result.valid_records}")
print(f"Invalid: {result.invalid_records}")
print(f"Average satisfaction: {result.satisfaction.average_score}")

csv_data = export_results_to_csv_string(result)
```
