# MF-LOG-ANALYZER v2 인수 테스트 체크리스트

이 문서는 사용자가 직접 프로토타입과 패키징된 EXE를 확인할 때 사용하는 기준이다.
명령은 프로젝트 루트 `C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer`에서 실행한다.

## 1. 자동 테스트

```powershell
cd C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer\prototype
$env:QT_QPA_PLATFORM='minimal'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
$base = Join-Path $env:TEMP ('mflog-pytest-' + [guid]::NewGuid().ToString('N'))
$cache = Join-Path $env:TEMP ('mflog-pytest-cache-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -v --basetemp=$base -o cache_dir=$cache
```

수용 기준:

- 전체 테스트가 통과한다.
- `python.exe` 응용 프로그램 오류 창이 뜨지 않는다.
- Windows에서 repo 내부 `.pytest-tmp` 또는 `.pytest_cache` 잠금이 생기면 위 명령처럼 임시 경로를 외부로 지정해 재실행한다.

## 2. 대용량 CSV 성능

300k 행, 200개 센서 목표 데이터를 생성한다.

```powershell
.\.venv\Scripts\python.exe -m mflog_proto.data.synthetic_log --rows 300000 --channels 200 --output .\.generated\synthetic_300k_200.csv
```

벤치마크를 실행한다.

```powershell
.\.venv\Scripts\python.exe -m mflog_proto.benchmark.runner --target-benchmark --rows 300000 --channels 200 --input .\.generated\synthetic_300k_200.csv --json-output .\.generated\acceptance\target_300k_200.json --html-output .\.generated\acceptance\target_300k_200.html --playback-updates 900 --hover-queries 1000 --graph-channel-count 20 --graph-pixel-width 1200
```

수용 기준:

- CSV 로딩 15초 이하.
- 그래프 캐시 5초 이하.
- 첫 그래프 표시 1.5초 이하.
- hover p95 지연 80 ms 이하.
- workspace 복원 2초 이하.
- 메모리 RSS 2.5 GB 이하.

## 3. 기본 UI 동작

```powershell
.\.venv\Scripts\python.exe -m mflog_proto.app
```

수용 기준:

- 앱이 검은색/흰색 충돌 없이 지정된 어두운 UI 테마로 열린다.
- 좌측 패널에서 Time-Series Graph, GPS Map, G-G Diagram, 3D Vehicle Model, Data Analysis, Documents, Gauge Indicators, Tire Temperature, Video Sync 창을 추가할 수 있다.
- 우측 Properties 패널은 선택한 분석 창에 맞는 설정만 표시한다.
- 체크박스, 콤보박스, 입력창 텍스트가 어두운 배경에서도 읽힌다.
- 중앙 분석 창은 최대화 후에도 축소/복원/닫기 컨트롤이 유지되고, 테두리 드래그로 크기를 조절할 수 있다.

## 4. CSV 재생 동기화

수용 기준:

- CSV 업로드 전에는 하단 CSV Playback 도크가 비활성 상태 또는 업로드 안내 상태다.
- CSV 업로드 후 파일명, row 수, 전체 길이, 현재 시간, 현재 row, 샘플링 주기, 이벤트 수가 표시된다.
- 재생/일시정지, 처음, 이전 이벤트, 다음 이벤트, 0.25x/0.5x/1x/2x/4x 속도 선택이 동작한다.
- 슬라이더 seek 시 Time-Series 세로선, GPS 현재 위치, G-G 현재 가속도 점, 센서 카드, 이벤트 강조가 같은 시점으로 갱신된다.
- Time-Series plot hover는 시간, 센서명, 값, 단위를 표시하고, plot 클릭 시 해당 시간으로 이동한다.
- 다른 탭으로 이동했다 돌아와도 업로드한 CSV와 재생 위치가 유지된다.
- autosave 실패는 경고로만 표시되고 현재 CSV 세션 재생을 막지 않는다.

## 5. GPS, 기준 경로, 이상 경로

수용 기준:

- GPS Map은 모든 CSV 경로를 연하게 배경 route로 표시하고, 현재 재생 중인 경로와 현재 위치를 강조한다.
- `(0, 0)` 또는 범위 밖 GPS 좌표는 경로에 연결하지 않는다.
- 실제 지도 배경 옵션을 켜면 OpenStreetMap 타일이 GPS 좌표계에 맞게 정렬된다.
- 지도 타일 로딩이 실패해도 GPS 경로와 현재 위치는 계속 표시된다.
- Reference Route 편집 모드에서 지도 클릭으로 기준 경로점을 추가할 수 있고 START/END 마커가 표시된다.
- `.mflogroute` 저장/불러오기 후 경로 이름, 점 개수, START/END 위치가 복원된다.
- Ideal Path 옵션을 켜면 wheelbase, steering ratio, steering channel 기준의 bicycle model 경로가 실제 GPS 경로 위에 겹쳐 표시된다.

## 6. G-G, Time-Series, 센서 표시

수용 기준:

- CSV 업로드 전후 모두 G-G Diagram의 한계원이 보인다.
- 우측 설정에서 G 한계 반경을 조정하면 열려 있는 G-G 창과 새 G-G 창에 반영된다.
- G-G 점은 보정 가속도 채널을 우선 사용하고 현재 재생 시점 점을 강조한다.
- Time-Series 우측 설정에서 표시 채널, 선 색상, 선 굵기를 조정할 수 있다.
- 주요 센서 카드에는 RPM, VSS/GPS speed, Gear, Battery voltage, TPS, ax, ay, roll/pitch/yaw rate가 현재 재생 시점 기준으로 표시된다.
- Gauge Indicators 창은 RPM과 Speed를 속도계 형태로 표시하고 재생 시점에 맞춰 갱신된다.
- Tire Temperature 창은 FL/FR/RL/RR 패널을 표시하고, 센서가 없으면 `-`로 표시한다.

## 7. 3D 차량 모델

수용 기준:

- 기본 `car.glb`가 로드되고 실제 GLB mesh가 viewport에 표시된다.
- 우측 Properties의 Vehicle GLB 설정에서 다른 `.glb` 모델을 로드할 수 있다.
- 선택한 GLB 경로는 `.mflogproj` 저장/불러오기 후 유지된다.
- 차량 중심에 XYZ 축이 표시된다.
- 현재 보정 ax/ay와 yaw rate에 따라 차량 roll/pitch/yaw 시각화가 갱신된다.
- Roll, Pitch, Yaw 숫자 표시가 작은 창 크기에서도 깨지지 않는다.

## 8. GoPro Video Sync

수용 기준:

- 좌측 패널에서 `Video Sync` 창을 추가할 수 있다.
- Video Sync 창에서 GoPro 주행 영상을 로드하면 현재 CSV 재생 시간과 `video offset` 기준으로 영상 위치가 동기화된다.
- CSV 재생/일시정지/속도 변경/seek 시 영상도 같은 기준 시간으로 이동한다.
- Video Sync 창 내부의 `-1000`, `-100`, `+100`, `+1000` offset 버튼을 누르면 우측 Properties, 다른 Video Sync 창, 새로 여는 Video Sync 창에 같은 offset이 반영된다.
- offset 또는 mute만 변경해도 영상 source가 다시 로드되지 않는다.
- 우측 Properties에서 video path, offset, mute를 설정하면 열려 있는 Video Sync 창과 새 Video Sync 창에 반영된다.
- `.mflogproj` 저장/불러오기 후 video path, offset, mute 상태가 복원된다.
- 프로젝트에 저장된 영상 파일이 사라진 경우 중앙 Video Sync 창과 우측 Properties 모두 `Video missing` 경고를 표시하고 프로젝트 복원은 계속 완료된다.

## 9. 프로젝트 저장/복원

수용 기준:

- `File > Save Project`와 `File > Open Project`로 CSV 경로, 재생 시간, 열린 분석 창, 탭 순서, 선택 채널, 차량 모델, 기준 경로, Video Sync 상태가 복원된다.
- 누락된 CSV/기준 경로/영상 파일은 경고 또는 빈 상태로 처리되고 앱 실행 자체를 막지 않는다.
- Event Review의 확인/무시 상태와 메모가 저장/복원된다.
- Segment Analysis의 사용자 구간이 저장/복원된다.
- Export Report는 세션 요약, 선택 채널, 이벤트 리뷰, 구간 요약을 포함한 HTML을 생성한다.

## 10. Windows EXE 빌드와 스모크 테스트

```powershell
cd C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer\prototype
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

기대 산출물:

```text
prototype\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe
```

수용 기준:

- EXE가 5초 이상 크래시 없이 실행된다.
- 프로그램 아이콘은 흰색 배경의 파란색 무한질주 로고로 표시된다.
- 번들된 `car.glb`와 문서 파일이 EXE 실행 환경에서도 로드된다.
- GoPro Video Sync 창이 EXE 환경에서도 추가되고, 영상 파일 선택 UI가 열린다.

필요 시 배포 압축 파일을 만든다.

```powershell
Compress-Archive -Path .\dist\MF-LOG-ANALYZER-v2 -DestinationPath .\dist\MF-LOG-ANALYZER-v2.zip -Force
```
