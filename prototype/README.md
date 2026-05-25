# MF-LOG-ANALYZER v2 Prototype

This folder contains the technology-validation prototype for MF-LOG-ANALYZER v2.

The prototype measures whether Python, PySide6/Qt, pyqtgraph, numpy, and polars can support the target workload of 300,000 rows and 100-200 sensor channels.

## Local Commands

```powershell
cd prototype
python -m venv .venv
.\.venv\Scripts\python -m pip install -e '.[dev]'
$env:QT_QPA_PLATFORM='minimal'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
.\.venv\Scripts\python -m pytest tests
.\.venv\Scripts\python -m mflog_proto.benchmark.runner
.\.venv\Scripts\python -m mflog_proto.data.synthetic_log --rows 300000 --channels 200 --output .generated/synthetic_300k_200.csv
.\.venv\Scripts\python -m mflog_proto.benchmark.runner --target-benchmark --input .generated/synthetic_300k_200.csv --json-output .generated/acceptance/target_300k_200.json --html-output .generated/acceptance/target_300k_200.html
```

The benchmark command records missing optional dependencies instead of hiding them. Install the dependencies before running UI and full CSV-performance validation.

After installing the package in an environment that has the prototype dependencies, use:

```powershell
mflog-proto-bench
mflog-proto-generate --rows 300000 --channels 200 --output .generated/synthetic_300k_200.csv
mflog-proto-bench --target-benchmark --input .generated/synthetic_300k_200.csv --json-output .generated/acceptance/target_300k_200.json --html-output .generated/acceptance/target_300k_200.html
mflog-proto-ui
```

The default benchmark command prints dependency/readiness metadata. Add
`--target-benchmark` to run measured CSV loading, mapping, derived-channel,
health-check, graph-cache, playback, hover, first-plot, workspace-restore, and
memory gates against the input CSV.

Pytest defaults to Qt's `minimal` platform on Windows because pyqtgraph can crash
intermittently during `offscreen` teardown. Use `offscreen` only for explicit
screenshot smoke scripts, and keep `QT_QPA_FONTDIR=C:\Windows\Fonts` so Qt can
find Korean fonts.

## Windows EXE Build

After installing the dev extras, build the onedir Windows executable with:

```powershell
cd prototype
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

The runnable app is created at:

```text
prototype\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe
```

To make a portable archive for handoff:

```powershell
Compress-Archive -Path .\dist\MF-LOG-ANALYZER-v2 -DestinationPath .\dist\MF-LOG-ANALYZER-v2.zip -Force
```

The PyInstaller spec bundles the root `car.glb` and `데이터분석기 콘티.pdf`
fixtures so the packaged prototype can open the 3D vehicle and document list
without depending on the source checkout.
