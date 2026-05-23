# MF-26

MF-26 자작자동차 프로젝트 저장소입니다. 현재 이 저장소에는 전장팀 작업을 위한 **Muzil Tools** 앱이 포함되어 있습니다.

## Muzil Tools

**Muzil Tools**는 MF-26 engine/elec 팀을 위한 로그 재생 및 배선 디버깅 워크벤치입니다.

주요 목적은 다음과 같습니다.

- EMU-LOGGER로 기록한 CSV 로그를 업로드해 주행 데이터를 재생합니다.
- 센서 4개를 한 그래프에 오버랩해 시간축 기준으로 비교합니다.
- GPS 경로, G-G 다이어그램, 이벤트/이상 감지를 함께 확인합니다.
- EasyEDA 회로도 JSON을 업로드해 ECU, 커넥터, 센서 핀 연결을 추적합니다.
- 배선도 이미지, 대회 규정, 데이터시트 링크를 프로젝트 자료로 모아둡니다.

앱 경로:

```text
Elec_app/
```

## 실행 방법

Node.js가 설치되어 있어야 합니다.

처음 실행할 때:

```powershell
cd Elec_app
npm install
npm run dev
```

이후 다시 실행할 때:

```powershell
cd Elec_app
npm run dev
```

개발 서버가 실행되면 브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:5173/
```

## 개발 명령어

```powershell
cd Elec_app
```

개발 서버:

```powershell
npm run dev
```

빌드 확인:

```powershell
npm run build
```

테스트:

```powershell
npm test
```

## 사용 흐름

### 1. 프로젝트 불러오기

`프로젝트` 메뉴에서 EasyEDA JSON 또는 Muzil Tools 프로젝트 파일을 업로드합니다.

EasyEDA JSON을 새로 업로드하면 기존 부품 분류 정보와 가능한 항목을 매칭해서 유지합니다.

### 2. 배선 디버거

`배선 디버거` 메뉴에서 ECU 핀, 커넥터, 센서명, net 이름을 검색합니다.

확인할 수 있는 정보:

- 핀과 연결된 다른 지점
- 커넥터 pinout
- 부품 역할 분류
- 현장 메모와 측정값

### 3. 로그 재생

`로그 재생` 메뉴에서 EMU-LOGGER CSV 파일을 업로드합니다.

확인할 수 있는 정보:

- 재생/정지/배속/시크바
- 현재 시점 주요 센서 카드
- 센서 4개 오버랩 그래프
- GPS 경로
- G-G 다이어그램
- 이벤트/이상 감지 리스트

### 4. 자료 보관함

`자료 보관함` 메뉴에서 배선도 이미지, 대회 규정, 데이터시트 링크 또는 파일을 프로젝트에 추가합니다.

## 인수테스트 체크리스트

- [ ] 앱이 `http://127.0.0.1:5173/`에서 열린다.
- [ ] `프로젝트`에서 EasyEDA JSON을 업로드할 수 있다.
- [ ] `배선 디버거`에서 부품/핀/커넥터 검색이 동작한다.
- [ ] 커넥터 pinout과 연결 trace를 확인할 수 있다.
- [ ] `자료 보관함`에서 배선도, 규정, 데이터시트를 추가할 수 있다.
- [ ] `로그 재생`에서 EMU-LOGGER CSV를 업로드할 수 있다.
- [ ] 로그 재생바를 움직이면 그래프의 현재 위치가 같이 바뀐다.
- [ ] 센서 오버랩 그래프에서 최대 4개 센서를 선택할 수 있다.
- [ ] GPS와 G-G 다이어그램이 CSV 데이터에 맞게 표시된다.
- [ ] 새로고침 후 프로젝트 정보가 유지된다.

## 폴더 구조

```text
MF-26/
├─ Elec_app/              # Muzil Tools React/Vite 앱
│  ├─ src/domain/         # EasyEDA, 배선, 로그 파싱/분석 로직
│  ├─ src/storage/        # 프로젝트 저장/불러오기
│  ├─ src/ui/             # 화면 컴포넌트
│  └─ public/             # PWA manifest, service worker
├─ BSPD/
├─ DataLog_Analyze/
├─ EassyEDA/
└─ docs/solutions/        # 구현 중 발견한 재발 방지 기록
```

## 참고

- 현재 실시간 텔레메트리 분석은 별도 프로젝트/담당에서 분리하는 방향입니다.
- Muzil Tools는 기록된 로그 재생, 배선 확인, 자료 관리에 집중합니다.
- EMU-LOGGER UI 구조를 참고했지만, 이 앱은 실시간 대시보드가 아니라 디버깅 워크벤치로 구성되어 있습니다.

