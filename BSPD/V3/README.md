## MF-26 BSPD(Brake System Plausibility Device)
순천향대학교 무한질주 MF-26을 위한 BSPD(제동시스템 타당성 장치) 프로젝트입니다.

### schematic


### PCB
<img width="1168" height="1157" alt="image" src="https://github.com/user-attachments/assets/218edc4b-d338-40d8-9cc4-44916b931d2c" />

#### 가변저항
DELAY_REF_V: RC 지연을 조정하기 위한 가변저항

BRAKE_REF_V: 브레이크 센서의 정상범위를 설정하기 위한 가변저항

TPS1_REF_V: TPS1의 정상범위 설정하기 위한 가변저항

TPS2_REF_V: TPS2의 정상범위를 설정하기 위한 가변저항

#### TP(TEST POINT)
- THROTTLE_OPENED: 스로틀 센서의 출력이 임계값을 넘으면 HIGH
- BRAKE_HARD: 브레이크 센서의 출력이 임계값을 넘으면 HIGH
- BSPD_COND_ERR_RC
- BPSD_COND_ERR_CLK
- SENSOR_RANGE_ERR_CLK
- BSPD_ACTIVATED
- BRAKE_RAW_SIG
- TPS1_RAW_SIG
- TPS2_RAW_SIG
- BRAKE_UNDER_REF_V
- BRAKE_OVER_REF_V
- BRAKE_ERR_RC
- TPS1_UNDER_REF_V
- TPS1_OVER_REF_V
- TPS1_ERR_RC
- TPS2_UNDER_REF_V
- TPS2_OVER_REF_V
- TPS2_ERR_RC
