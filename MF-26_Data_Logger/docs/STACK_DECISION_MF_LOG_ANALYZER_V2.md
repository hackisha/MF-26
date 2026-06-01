# MF-LOG-ANALYZER v2 Prototype Stack Decision

Date: 2026-05-25

## Decision

Keep the candidate stack for the next implementation slice:

- Python 3.12
- PySide6/Qt
- pyqtgraph
- numpy
- polars
- psutil
- pytest/pytest-qt

The measured prototype run passed the 300,000-row x 200-channel target gates on
the local Windows workstation. Native acceleration is not required for the first
production slice, but the graph-cache boundary should stay isolated because it
was the only measured hotspot before numpy-array optimization.

## Evidence

Primary reports:

```text
prototype\.generated\acceptance\target_300k_200.json
prototype\.generated\acceptance\target_300k_200.html
```

Measured target input:

```text
prototype\.generated\synthetic_300k_200.csv
rows: 300000
channels: 200
size: 615621732 bytes
```

Key results from the latest run:

| Category | Gate | Measured |
| --- | ---: | ---: |
| CSV loading | <= 15 s | 0.603 s |
| Mapping | <= 5 s | 0.0002 s |
| Derived channels | <= 5 s | 0.042 s |
| Health checks | <= 5 s | 0.157 s |
| Graph cache | <= 5 s | 0.793 s |
| First plot | <= 1.5 s | 0.292 s |
| Workspace restore | <= 2 s | 0.403 s |
| Hover latency p95 | <= 80 ms | 0.0027 ms |
| Memory RSS | <= 2.5 GB | 0.694 GB |

Playback cursor measurement exceeded the 30 Hz target in the benchmark update
loop. The prototype also ran an 8 time-series window plus G-G plus current-values
window smoke in 0.511 s.

## Notes

- The default readiness report intentionally leaves performance categories as
  `PENDING`; use `--target-benchmark` for measured pass/fail.
- Normal pytest uses Qt `minimal` on Windows. `offscreen` remains reserved for
  isolated screenshot smoke scripts because it can trigger native teardown
  crashes with PySide6/pyqtgraph.
- The SRS file originally referenced by the user is not present under
  `docs/superpowers/specs/` in this workspace. This decision uses the current
  prototype and implementation plans as the local acceptance basis.

## Next Implementation Slice

Start production Milestones 0-4 from
`docs/superpowers/plans/2026-05-25-mf-log-analyzer-v2-implementation.md`:

1. repository and engineering baseline
2. data foundation
3. profiles and standard channel mapping
4. units/calibration/derived channels
5. health-check/event foundation

Keep graph-cache/downsampling behind an interface and preserve the numpy-array
path used in the prototype benchmark.
