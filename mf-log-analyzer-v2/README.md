# MF-LOG-ANALYZER v2

Python/Qt performance-validation implementation for the MF-LOG-ANALYZER v2 SRS.

## Development

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -e ".[dev]"
.\\.venv\\Scripts\\python -m pytest
.\\.venv\\Scripts\\python -m mf_log_analyzer_v2
```

## Foundation Benchmark

Local benchmark target:

- 300,000 rows
- MF default profile channel mapping
- column-oriented Polars load

Latest local result:

```text
rows=300000
load_seconds=0.405
```
