# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## `analyze.py` — Incident File Analyzer

CLI tool to analyze Nexova helpdesk incident CSV exports for volume, valid/invalid breakdown, categories distribution, and satisfaction scores without leaking customer PII.

### Usage

```bash
# Run analysis on the official fixture
python scripts/analyze.py data/raw/incidents-nexova.csv

# Or run from inside scripts/ directory
cd scripts
python analyze.py incidents-nexova.csv
```

### Options
- `--export`: Automatically export summary metrics to `results.csv` without interactive prompting.
- `--no-export`: Skip export without prompting.
- `-o <filename>`, `--output <filename>`: Specify custom destination path for the exported summary CSV.

### Testing

```bash
python -m unittest discover -s packages/incident_analyzer/tests -v
```

> _Spanish version: [README.es.md](./README.es.md)._
