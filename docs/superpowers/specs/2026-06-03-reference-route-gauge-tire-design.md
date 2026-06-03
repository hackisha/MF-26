# MF-LOG-ANALYZER Reference Route, Gauge, Tire Temperature Design

## 목적

GPS 기반 기준 주행 경로를 앱 안에서 만들고 저장/불러온 뒤, 실제 CSV 주행 경로와 GPS Map 위에서 비교할 수 있게 한다. 동시에 RPM/속도처럼 순간값을 빠르게 읽어야 하는 센서는 게이지형 인디케이터로 보여주고, 추후 타이어 온도 센서가 추가될 때 바로 시각화할 수 있는 타이어 온도 창을 준비한다.

GoPro 주행 영상 동기화 분석은 이번 구현 범위에서 제외한다. 이번 기능이 완료된 뒤 playback timeline을 공유하는 별도 설계로 다룬다.

## 범위

이번 1차 구현에 포함한다.

- GPS Map에서 기준 경로 점을 클릭으로 추가하고 초기화할 수 있다.
- 기준 경로의 시작점과 종료점을 별도 마커로 표시한다.
- 기준 경로를 JSON 기반 `.mflogroute` 파일로 저장하고 불러온다.
- 불러온 기준 경로를 실제 주행 GPS 경로, ideal path와 함께 오버레이한다.
- 좌측 패널에 `Gauge Indicators` 분석 창을 추가한다.
- `Gauge Indicators` 창에서 RPM과 GPS/VSS 속도를 playback 시점에 맞춰 게이지로 표시한다.
- 좌측 패널에 `Tire Temperature` 분석 창을 추가한다.
- 타이어 온도 센서가 없을 때도 FL/FR/RL/RR placeholder가 보이고, 센서가 감지되면 온도 숫자와 색상 막대가 갱신된다.

이번 1차 구현에서 제외한다.

- 기준 경로 점 드래그 이동, 점 단위 삭제, 스냅 편집
- 경로별 목표 속도, 섹터, 시뮬레이션 파라미터 편집
- GoPro/외부 영상 동기화
- 동역학 시뮬레이션 실행

## 사용자 흐름

1. 사용자가 CSV를 업로드하면 기존처럼 실제 GPS 주행 경로가 GPS Map에 표시된다.
2. 사용자가 GPS Map 창을 선택하면 우측 속성 패널에 Reference Route 도구가 표시된다.
3. 사용자가 `Edit route`를 켜고 지도 위를 클릭하면 기준 경로 점이 순서대로 추가된다.
4. 기준 경로가 2점 이상이면 시작점과 종료점이 보이고, 경로 선이 실제 주행 경로와 다른 색으로 표시된다.
5. 사용자는 기준 경로를 `.mflogroute`로 저장하거나 기존 파일을 불러온다.
6. 사용자는 좌측 패널에서 `Gauge Indicators`를 열어 RPM과 속도를 현재 playback 시점 기준으로 확인한다.
7. 사용자는 좌측 패널에서 `Tire Temperature`를 열어 현재 또는 미래의 타이어 온도 센서 값을 확인한다.

## 데이터 모델

새 모듈 `mflog_proto.analysis.reference_route`를 둔다.

`ReferenceRoutePoint`

- `latitude`: float
- `longitude`: float

`ReferenceRoute`

- `name`: str
- `points`: tuple[ReferenceRoutePoint, ...]
- `source_path`: Path | None
- `created_at`: ISO 8601 문자열
- `metadata`: dict[str, str]

저장 형식은 JSON으로 시작한다. 확장자는 `.mflogroute`를 사용한다.

```json
{
  "schema_version": 1,
  "name": "Endurance reference",
  "created_at": "2026-06-03T00:00:00+09:00",
  "points": [
    {"latitude": 35.29301, "longitude": 126.574061}
  ],
  "metadata": {}
}
```

좌표 데이터는 GPS Map, 향후 시뮬레이션, 리포트에서 재사용할 수 있도록 UI 클래스에 직접 묶지 않는다.

## GPS Map 설계

`GPSMapWindow`에 기준 경로 전용 레이어를 추가한다.

- 실제 주행 경로: 기존 파란색 계열 유지
- 전체 배경 경로: 기존처럼 연하게 표시
- ideal path: 기존 노란색 계열 유지
- reference route: 녹색/민트 계열 점선 또는 실선으로 표시
- 시작점: `START` 마커
- 종료점: `END` 마커

마우스 hover는 기존 GPS hover 구조를 확장한다. 기준 경로 위에 마우스를 올리면 `Reference | route name | point index | lat/lon`을 표시한다. 실제 주행 경로 hover와 playback seek 동작은 기존처럼 유지한다.

편집 모드에서는 GPS Map 클릭을 playback seek로 해석하지 않고 기준 경로 점 추가로 해석한다. 편집 모드가 꺼져 있으면 기존 상호작용을 유지한다.

## 우측 속성 패널

GPS Map 선택 시 기존 GPS 설정 아래에 Reference Route 그룹을 추가한다.

- `Edit route`: 지도 클릭으로 기준 경로 점 추가
- `Route name`: 기준 경로 이름
- `Load`: `.mflogroute` 파일 불러오기
- `Save`: 현재 기준 경로 저장
- `Clear`: 현재 기준 경로 초기화
- `Points`: 현재 기준 경로 점 개수 표시

파일 저장/불러오기 실패는 상태바 경고로 표시하고 현재 세션을 막지 않는다.

## Gauge Indicators 창

좌측 패널 `시각화` 그룹에 `Gauge Indicators`를 추가한다.

창은 두 개의 기본 게이지를 표시한다.

- RPM: 기본 범위 0-9000 rpm
- Speed: GPS speed 또는 VSS/GPS speed를 자동 선택, 기본 범위 0-180 km/h

게이지는 PySide6 `QWidget.paintEvent` 기반 커스텀 위젯으로 구현한다. 새 렌더링 의존성을 추가하지 않는다. playback state가 바뀌면 현재 sample index의 값을 읽고 needle, 숫자, 단위를 갱신한다. 값이 없으면 `-`를 표시하고 needle은 0 위치로 둔다.

## Tire Temperature 창

좌측 패널 `시각화` 그룹에 `Tire Temperature`를 추가한다.

창은 FL/FR/RL/RR 4개 패널을 표시한다. 각 패널은 다음 요소를 가진다.

- 좌측 상단 위치 라벨: `FL`, `FR`, `RL`, `RR`
- 중앙 타이어 실루엣
- 옆쪽 세로 온도 막대: 파랑에서 빨강으로 그라데이션
- 현재 온도 숫자: `72.4 C` 형식

센서 자동 매핑은 흔한 이름을 우선 지원한다.

- FL: `Tire_FL_C`, `FL_TireTemp_C`, `TireTemp_FL`, `FL_temp`
- FR: `Tire_FR_C`, `FR_TireTemp_C`, `TireTemp_FR`, `FR_temp`
- RL: `Tire_RL_C`, `RL_TireTemp_C`, `TireTemp_RL`, `RL_temp`
- RR: `Tire_RR_C`, `RR_TireTemp_C`, `TireTemp_RR`, `RR_temp`

센서가 없으면 각 패널은 `-`와 중립 색상을 표시한다. 온도 범위는 20-120 C를 기본으로 사용한다.

## 프로젝트 저장

기준 경로는 `.mflogproj`에 전체 좌표를 직접 저장하지 않는다. 재사용 가능한 별도 `.mflogroute` 파일이 주 저장 단위다.

단, 프로젝트에는 마지막으로 불러온 기준 경로 파일 경로와 현재 route name을 저장할 수 있도록 확장한다. 해당 파일이 없으면 경고만 표시하고 프로젝트 복원은 계속한다.

## 테스트 전략

단위 테스트를 먼저 추가한다.

- `.mflogroute` 저장/불러오기 round trip
- 잘못된 route JSON을 안전하게 거부
- `GPSMapWindow`가 기준 경로, 시작점, 종료점을 표시
- 편집 모드 클릭이 기준 경로 점을 추가
- `Gauge Indicators`가 playback index에 따라 RPM/속도 값을 갱신
- `Tire Temperature`가 센서 유무에 따라 값 또는 placeholder를 표시
- 좌측 패널과 `add_analysis_window`가 새 창 2개를 실제 위젯으로 연결

검증은 기존 PySide6 pytest 흐름을 따른다. 전체 테스트는 `QT_QPA_PLATFORM=minimal`, `QT_QPA_FONTDIR=C:\Windows\Fonts` 환경에서 실행한다.

## 수용 기준

- GPS Map에서 기준 경로를 클릭으로 만들고 시작/종료 마커를 볼 수 있다.
- 기준 경로를 `.mflogroute`로 저장하고 다시 불러오면 동일한 점들이 복원된다.
- CSV 실제 GPS 경로와 기준 경로가 같은 GPS Map 위에 동시에 표시된다.
- 기준 경로 hover 정보가 표시된다.
- `Gauge Indicators` 창이 좌측 패널에서 추가되고 RPM/속도가 playback과 동기화된다.
- `Tire Temperature` 창이 좌측 패널에서 추가되고 센서가 없을 때도 미래 센서용 UI가 깨지지 않는다.
- 기존 CSV playback, GPS Map 실제 지도 옵션, ideal path, Time-Series Graph 선택 채널 기능이 회귀하지 않는다.

