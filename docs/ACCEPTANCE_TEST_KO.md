# MF-LOG-ANALYZER v2 프로토타입 인수테스트

이 문서는 사용자가 직접 프로토타입 상태를 확인할 때 쓰는 실행 체크리스트입니다.
모든 명령은 프로젝트 루트에서 실행하는 것을 기준으로 합니다.

```powershell
cd C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer
$env:QT_QPA_PLATFORM='minimal'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
```

Windows에서 `QT_QPA_PLATFORM=minimal` 설정은 의도된 값입니다. 일반 pytest
검증에서는 `offscreen`을 쓰지 마세요. PySide6/pyqtgraph 종료 과정에서
`python.exe` 네이티브 오류창이 뜰 수 있습니다.

## 1. 자동 테스트

```powershell
.\prototype\.venv\Scripts\python -m pytest .\prototype\tests
```

기대 결과:

- 전체 테스트가 통과합니다.
- `python.exe` 응용 프로그램 오류창이 뜨지 않습니다.
- 최신 검증 기준으로는 `126 passed`가 정상입니다.

## 2. 300k x 200 합성 CSV 생성

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.data.synthetic_log --rows 300000 --channels 200 --output .\prototype\.generated\synthetic_300k_200.csv
```

생성되는 입력 파일:

```text
prototype\.generated\synthetic_300k_200.csv
```

이미 파일이 있으면 다시 만들지 않고 다음 단계의 벤치마크에 그대로 사용할 수
있습니다.

## 3. 준비 상태 리포트

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.benchmark.runner --json-output .\prototype\.generated\acceptance\benchmark_readiness.json --html-output .\prototype\.generated\acceptance\benchmark_readiness.html
```

이 리포트는 Python, PySide6, pyqtgraph, numpy, polars 같은 의존성이 준비됐는지
확인합니다. 실제 성능 측정값은 다음 단계의 `--target-benchmark` 실행에서
생성됩니다.

산출물:

```text
prototype\.generated\acceptance\benchmark_readiness.json
prototype\.generated\acceptance\benchmark_readiness.html
```

## 4. 300k x 200 목표 벤치마크

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.benchmark.runner --target-benchmark --rows 300000 --channels 200 --input .\prototype\.generated\synthetic_300k_200.csv --json-output .\prototype\.generated\acceptance\target_300k_200.json --html-output .\prototype\.generated\acceptance\target_300k_200.html --playback-updates 900 --hover-queries 1000 --graph-channel-count 20 --graph-pixel-width 1200
```

주요 산출물:

```text
prototype\.generated\acceptance\target_300k_200.json
prototype\.generated\acceptance\target_300k_200.html
```

최신 로컬 실행일인 2026-05-25 기준으로 모든 프로토타입 성능 게이트를
통과했습니다.

| 항목 | 최신 측정값 |
| --- | ---: |
| CSV 로딩 | 0.603 s |
| 채널 매핑 | 0.0002 s |
| 파생 채널 계산 | 0.042 s |
| 로그 헬스 체크 | 0.157 s |
| 그래프 캐시 생성 | 0.793 s |
| 재생 커서 업데이트 루프 | 227,710 Hz |
| Hover p95 지연 | 0.0027 ms |
| 첫 그래프 표시 | 0.292 s |
| 워크스페이스 복원 | 0.403 s |
| 다중 창 업데이트 스모크 | 0.480 s |
| 메모리 RSS | 0.694 GB |

통과 기준은 다음과 같습니다.

- CSV 로딩: 15초 이하
- 매핑/파생/헬스 체크: 각 5초 이하
- 그래프 캐시: 5초 이하
- 첫 그래프 표시: 1.5초 이하
- Hover p95 지연: 80 ms 이하
- 워크스페이스 복원: 2초 이하
- 메모리 RSS: 2.5 GB 이하

## 5. 결함 포함 CSV 스모크

결함 데이터 처리 경로를 확인하려면 아래 명령을 실행합니다.

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.benchmark.runner --target-benchmark --generate --defects --rows 32 --channels 25 --input .\prototype\.generated\acceptance\target_defects_smoke.csv --json-output .\prototype\.generated\acceptance\target_defects_smoke.json --html-output .\prototype\.generated\acceptance\target_defects_smoke.html --graph-channel-count 2 --playback-updates 4 --hover-queries 4
```

기대 결과:

- timestamp duplicate/backward 문제가 health-check details에 기록됩니다.
- UI metric 경로가 sorted x 오류 없이 끝까지 실행됩니다.
- `QT_QPA_PLATFORM`이 이전 세션에서 `offscreen`으로 남아 있어도 benchmark 내부에서
  `minimal`로 강제됩니다.

## 6. 수동 UI 스모크

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.app
```

확인할 항목:

- 앱 창이 정상적으로 열립니다.
- 왼쪽 분석 목록에서 분석 창을 추가할 수 있습니다.
- 우측 속성 패널에서 좌측 분석 패널의 검색창 표시, 추가 버튼 표시, 기본/A-Z 정렬,
  Compact/Comfortable 밀도, 패널 폭을 조정할 수 있습니다.
- CSV가 없는 초기 상태에서는 하단 재생 도크가 비활성화되고 업로드 안내가 표시됩니다.
- `File > Open CSV`로 루트 샘플 CSV를 열면 파일명, row 수, 전체 길이, 현재 시간,
  현재 row, 추정 샘플링 주기, 이벤트 수가 하단 도크에 표시됩니다.
- CSV malformed row 진단은 경고로만 표시되고 재생을 막지 않습니다.
- `File > Save Project`와 `File > Open Project`로 `.mflogproj` 파일에 CSV 경로,
  재생 시간, 탭 순서, 열린 분석 창이 왕복 저장됩니다.
- 재생/일시정지, 처음 이동, 끝 이동, 이전/다음 이벤트 이동, 0.25x/0.5x/1x/2x/4x 속도 선택,
  슬라이더 seek가 동작합니다.
- 슬라이더를 움직이면 Time-Series 세로선, GPS 현재 위치점, G-G 현재 가속도점,
  주요 센서 카드 값, 이벤트 강조가 같은 현재 시점으로 갱신됩니다.
- 중앙 작업영역의 분석 창을 최대화해도 창 내부 우상단에 최소화/복원/닫기 컨트롤이
  계속 표시됩니다.
- 설정/우측 속성 패널에서 GPS 실제 지도 배경 레이어를 켜고 끌 수 있습니다.
  네트워크/캐시 접근이 가능하면 OpenStreetMap 타일이 전체 경로 뒤에 표시되고,
  타일이 없어도 재생, 전체 경로, 현재 위치점은 계속 동작합니다. 같은 패널에서
  시계열 그래프의 선 색상/굵기와 G-G 한계원 반경도 조정할 수 있으며, 이미 열린 창과
  새로 여는 창 모두 설정을 반영합니다.
- GPS 경로는 `(0, 0)` 또는 범위를 벗어난 무효 좌표 샘플을 연결하지 않고 건너뜁니다.
- CSV 업로드 후에도 G-G 다이어그램의 1 G 한계원이 보이고, `ax_g`/`ay_g`는
  ADXL345 보정 가속도로 표시됩니다.
- 탭을 이동했다가 돌아와도 CSV 세션과 재생 위치가 유지됩니다.
- Time-Series, GPS, G-G plot hover 시 가장 가까운 샘플의 시간과 plot별 값이
  라벨/tooltip에 표시되고, Time-Series 그래프 클릭 시 해당 시간으로 이동합니다.
- 자동 저장 실패 경고가 표시되어도 현재 CSV 세션과 재생 기능은 유지됩니다.
- `3D Vehicle Model` 창이 프로젝트 루트의 `car.glb`를 읽고, 렌더링 가능한
  mesh vertex/triangle을 파싱한 뒤 viewport에 실제 GLB mesh와 정성적 시각화
  안내를 표시합니다.

## 7. Windows EXE 빌드 스모크

```powershell
cd .\prototype
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

기대 산출물:

```text
prototype\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe
```

전달용 압축 파일이 필요하면 다음 명령으로 생성합니다.

```powershell
Compress-Archive -Path .\dist\MF-LOG-ANALYZER-v2 -DestinationPath .\dist\MF-LOG-ANALYZER-v2.zip -Force
```

생성된 exe를 실행해 앱 창이 열리고, `3D Vehicle Model`과 `Documents` 창에서
번들된 `car.glb`, `데이터분석기 콘티.pdf`를 확인합니다.

## 8. 판정

현재 프로토타입 기준 판정:

- Python + PySide6/Qt + pyqtgraph + numpy + polars 스택은 300k x 200 목표
  벤치마크를 통과했습니다.
- 네이티브 가속은 첫 구현 슬라이스에서 필수는 아닙니다.
- 그래프 캐시/다운샘플링 경로는 성능 핵심 구간이므로, production 구현에서도
  numpy 배열 기반 경로를 유지해야 합니다.

관련 결정 문서:

```text
docs\STACK_DECISION_MF_LOG_ANALYZER_V2.md
```
