# MF-LOG-ANALYZER v2 Prototype

This folder contains the technology-validation prototype for MF-LOG-ANALYZER v2.

The prototype measures whether Python, PySide6/Qt, pyqtgraph, numpy, and polars can support the target workload of 300,000 rows and 100-200 sensor channels.

## Local Commands

```powershell
cd prototype
python -m pytest
$env:PYTHONPATH='src'; python -m mflog_proto.benchmark.runner
python -m mflog_proto.data.synthetic_log --rows 300000 --channels 200 --output .generated/synthetic_300k_200.csv
```

The benchmark command records missing optional dependencies instead of hiding them. Install the dependencies before running UI and full CSV-performance validation.

After installing the package in an environment that has the prototype dependencies, use:

```powershell
mflog-proto-bench
mflog-proto-generate --rows 300000 --channels 200 --output .generated/synthetic_300k_200.csv
```
