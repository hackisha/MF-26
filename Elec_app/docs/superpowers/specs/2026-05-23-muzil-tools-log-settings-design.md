# Muzil Tools 로그 설정 및 분석 UX 설계

## 배경

Muzil Tools는 웹 UI 기반으로 계속 개발한다. 실시간 텔레메트리는 별도 프로젝트에서 담당하고, 이 앱은 기록된 CSV 로그 재생, 배선 확인, 자료 관리, MATLAB 연동을 고려한 분석 보조 도구에 집중한다.

기존 로그 재생 탭은 기본 기능은 갖췄지만 실제 분석 도구로 쓰기에는 다음 문제가 있다.

- 센서 오버랩 그래프에서 hover 시 실제 값과 센서명을 확인할 수 없다.
- 다른 탭으로 이동하거나 새로고침하면 CSV를 다시 업로드해야 한다.
- 주요 센서 카드가 오른쪽에 몰려 있어 가독성이 낮다.
- 데이터로거 UI와 다른 밝은 UI가 섞여 있어 분석 화면의 시각적 일관성이 낮다.
- GPS 경로가 위도/경도를 단순 x/y로 그려 찌그러질 수 있다.
- ADXL345 선형 가속도와 ADU 각가속도 계열이 명확히 분리되어 있지 않다.
- 센서 scale/offset, 단위, 수식, 경고 규칙을 사용자 설정으로 관리할 수 없다.

## 목표

로그 재생을 "업로드 후 보는 화면"에서 "사용자 정의 가능한 로그 해석 워크벤치"로 확장한다.

사용자는 CSV를 한 번 업로드한 뒤 다음을 할 수 있어야 한다.

- 탭 이동/새로고침 후에도 최근 로그를 유지한다.
- 센서 오버랩 그래프에서 마우스 hover로 시간, 센서명, 값, 단위를 확인한다.
- 데이터로거 스타일의 검정 배경/노란 강조 UI로 로그를 분석한다.
- Dashboard, Overlay, GPS, G-G/Accel, Events, Sensors, Settings 화면을 나눠 가독성을 높인다.
- ADXL345 선형 가속도와 ADU 각가속도 또는 각속도 계열을 별도 그룹으로 해석한다.
- 센서 표시명, 컬럼 alias, scale, offset, 단위, 색상, 그래프 표시 여부를 설정한다.
- 안전한 자유수식 센서를 추가한다.
- 이벤트/경고 규칙과 그래프 프리셋을 설정한다.
- MATLAB 연동을 위해 설정 JSON과 분석 결과 export 구조를 유지한다.

## 비목표

- 이번 단계에서 사용자 계정, 클라우드 동기화, 백엔드 서버를 만들지 않는다.
- MATLAB Engine을 앱 내부에서 직접 실행하지 않는다.
- 모든 수식 언어를 지원하지 않는다. 안전한 제한 수식만 지원한다.
- 실시간 텔레메트리 수신 기능은 만들지 않는다.

## 정보 구조

로그 재생 영역은 내부 탭으로 분리한다.

1. `Dashboard`
   - 데이터로거 스타일의 검정 배경, 노란 강조 색상
   - RPM, Gear, Speed, 주요 게이지
   - 주요 센서는 설정의 dashboard preset을 따른다.

2. `Overlay`
   - 센서 최대 4개 오버랩 그래프
   - hover tooltip: 시간, 센서명, 값, 단위
   - 현재 재생 위치 세로선
   - 그래프 프리셋 선택

3. `GPS`
   - 위도/경도 중심점 기준 근사 투영
   - 현재 위치 marker
   - 속도 컬러 또는 단일 강조 색상
   - GPS jump threshold 설정 반영

4. `G-G / Accel`
   - G-G는 선형 가속도 X/Y만 사용
   - ADXL345는 `linear-accel` 그룹
   - ADU x/y/z는 `angular` 그룹
   - 축 반전, 축 교환, scale, offset 설정 반영

5. `Events`
   - 이상 감지 목록
   - 클릭 시 해당 시간으로 seek
   - 설정의 이벤트 규칙 기반 warning/danger 표시

6. `Sensors`
   - 전체 센서 테이블
   - 원본 값, 보정 값, 파생 값 구분
   - 검색/필터

7. `Settings`
   - 센서 정의
   - 컬럼 alias
   - 자유수식 센서
   - 이벤트/경고 규칙
   - 그래프 프리셋
   - ADXL/ADU 보정
   - GPS 설정
   - export/import

## 데이터 모델

### LogReplaySettings

```ts
interface LogReplaySettings {
  version: 1;
  sensors: SensorConfig[];
  derivedSensors: DerivedSensorConfig[];
  eventRules: EventRuleConfig[];
  graphPresets: GraphPresetConfig[];
  gps: GpsConfig;
  accel: AccelConfig;
  matlab: MatlabExportConfig;
}
```

### SensorConfig

```ts
interface SensorConfig {
  id: string;
  sourceKey: string;
  aliases: string[];
  label: string;
  unit: string;
  group: "engine" | "electric" | "gps" | "linear-accel" | "angular" | "custom";
  scale: number;
  offset: number;
  precision: number;
  color: string;
  showInDashboard: boolean;
  showInOverlay: boolean;
  showInSensorTable: boolean;
}
```

### DerivedSensorConfig

```ts
interface DerivedSensorConfig {
  id: string;
  label: string;
  expression: string;
  unit: string;
  group: SensorConfig["group"];
  precision: number;
  color: string;
  fallback: "empty" | "zero" | "previous";
  enabled: boolean;
}
```

### EventRuleConfig

```ts
interface EventRuleConfig {
  id: string;
  label: string;
  expression: string;
  severity: "info" | "warning" | "danger";
  enabled: boolean;
}
```

### GraphPresetConfig

```ts
interface GraphPresetConfig {
  id: string;
  label: string;
  sensorIds: string[];
}
```

### GpsConfig

```ts
interface GpsConfig {
  latitudeKey: string;
  longitudeKey: string;
  speedKey: string;
  jumpThresholdMeters: number;
  smoothing: "off" | "light";
}
```

### AccelConfig

```ts
interface AccelConfig {
  linear: {
    xKey: string;
    yKey: string;
    zKey: string;
    unit: "g" | "mps2" | "raw";
    swapXY: boolean;
    invertX: boolean;
    invertY: boolean;
    invertZ: boolean;
    lowPassAlpha: number;
  };
  angular: {
    xKey: string;
    yKey: string;
    zKey: string;
    unit: "degps" | "radps" | "raw";
    scale: number;
    offset: number;
  };
}
```

## 수식 시스템

자유수식과 이벤트 규칙은 같은 안전 수식 엔진을 사용한다.

허용 문법:

- 숫자
- 센서 id 또는 sourceKey
- `+`, `-`, `*`, `/`
- 괄호
- 비교 연산: `>`, `>=`, `<`, `<=`, `==`, `!=`
- 논리 연산: `&&`, `||`
- 안전 함수: `min`, `max`, `abs`, `sqrt`, `round`, `floor`, `ceil`

금지:

- JavaScript `eval`
- 임의 함수 호출
- 객체 접근
- 배열 접근
- 문자열 실행

수식 계산 실패 시:

- 파생 센서는 `fallback` 정책을 따른다.
- 이벤트 규칙은 false로 처리하고 설정 화면에 오류를 표시한다.

## 저장 방식

1차 구현에서는 IndexedDB를 사용한다.

- 최근 CSV 원문 저장
- 최근 CSV 파일명 저장
- 파싱된 세션은 앱 시작 시 CSV 원문에서 재생성
- 설정 JSON 저장

localStorage는 작은 UI 상태만 저장한다.

저장 키:

- `muzil-tools/log-replay/latest-csv`
- `muzil-tools/log-replay/settings`
- `muzil-tools/log-replay/ui-state`

## MATLAB 연동

이번 단계에서는 직접 MATLAB을 실행하지 않는다.

대신 다음 export 기반을 만든다.

- 보정/파생 센서가 반영된 CSV export
- 설정 JSON export/import
- MATLAB용 변수명 규칙: 영문/숫자/underscore만 허용
- 향후 `.m` 스크립트 자동 생성과 `.mat` export를 추가할 수 있게 데이터 계층을 분리한다.

## 오류 처리

- CSV 컬럼이 설정 alias와 매칭되지 않으면 Settings에서 "매칭 안 됨" 상태를 표시한다.
- 자유수식에 존재하지 않는 센서가 있으면 저장 전에 오류를 보여준다.
- GPS 컬럼이 없으면 GPS 탭은 빈 상태를 보여준다.
- ADXL 또는 ADU 컬럼이 없으면 해당 패널만 빈 상태를 보여준다.
- IndexedDB 저장 실패 시 세션은 메모리에서 유지하고 사용자에게 저장 실패를 알린다.

## 테스트 기준

- 설정 기본값 생성 테스트
- 컬럼 alias 매칭 테스트
- scale/offset 적용 테스트
- 자유수식 계산 테스트
- 위험 수식 차단 테스트
- 이벤트 규칙 평가 테스트
- CSV 저장/복원 테스트
- GPS 투영 테스트
- Overlay tooltip 값 선택 테스트
- LogReplay 내부 탭 전환 시 세션 유지 테스트

