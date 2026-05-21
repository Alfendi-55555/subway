# MetroSim — 지하철 혼잡 처방 시뮬레이터

> "출근길 강남역, 왜 이렇게 막히는 걸까?"

매일 수백만 명이 이용하는 지하철. 특정 역에 승객이 몰리면 열차는 지연되고, 혼잡은 주변 역까지 번집니다.
MetroSim은 이러한 현실의 문제를 OOP 객체로 모델링해, 병목이 발생하는 구역을 해결하기 위한 시나리오를 실행하여 더 나은 해결 방안으로의 의사결정을 지원하고자 하는 목적으로 구성되었습니다.

---

## 예시 시나리오 흐름

```
07:00  시뮬레이션 시작. 역마다 승객이 조금씩 대기 중.
          ↓
07:30  출근 러시아워 돌입. 강남·교대·고속터미널·양재로 승객 쏠림.
          ↓
       병목 감지! "고속터미널역 32명 대기" 경고 발생.
          ↓
       우클릭 → 시나리오 분석: 현상유지 vs 무정차 분산 vs 열차 추가 중 평가 점수가 높은 추천 시나리오를 알려줍니다.
          ↓
       [적용] 버튼 클릭 → 추천 처방을 좌측 실시간 시뮬레이션에 반영
          ↓
       처방 효과를 실시간 확인
```

---

## 실행 방법

```powershell
python -m subway_sim_more
```
또는 main.py 파일 run

### 조작법

| **좌클릭** (역) | 무정차 처방 — 해당 역을 건너뛰고, 대기 승객을 인접 역으로 분산 |
| **우클릭** (역) | 시나리오 분석 — 1시간 고속 시뮬레이션으로 3가지 처방 비교 |
| **[적용] 버튼** | 분석 결과에서 원하는 처방을 화면 좌측의 실제 시뮬레이션에 적용 |

---

## 주요 기능

### 러시아워 시스템
- 시뮬레이션 내부 시간이 흐르며(1초에 내부 시간으로 약 2분), 07:30~09:30에 출근 러시아워 발생
- 러시아워 시 업무지구(강남, 교대, 고속터미널, 양재)로 승객 목적지 편향
- 외곽/주거지 역에서 출발 승객 증가 (출발역별 가중치)

### 병목 감지 & 시나리오 분석
- 30명 이상 대기 역을 자동 감지하여 병목 경고
- 해당 역을 우클릭 시 동일 조건(시드 고정)에서 3가지 처방을 비교한 결과를 확인할 수 있습니다.

| 시나리오 | 설명 |
|---|---|
| 현상유지 | 아무 조치 없이 1시간 경과 |
| 무정차 분산 | 해당 역을 무정차로 전환, 승객을 인접 역으로 분산 |
| 열차 추가 | 해당 역이 속한 노선에 열차 1대 추가 투입 |

- 처리량, 과부하 역 수, 노선 흐름을 종합하여 최적 처방을 도출합니다.
- [적용] 버튼으로 추천 처방을 즉시 반영 (열차 추가는 최대 3대 제한)

### 🚆 열차 운행 로직
- 노선 종점에서 자동 반전하며 왕복 운행
- 역 도착 시 목적지 승객 하차 → 탑승 가능 승객 승차 (정원 40명)
- 혼잡도 비례 정차 지연: 대기 승객이 많을수록 역 정차 시간 증가

---

## OOP 설계

### 클래스 구조

Simulation ─────── 시뮬레이션 상태와 규칙 (역, 노선, 열차, 시간)
│
├── Station ────────── 역: 대기 승객, 승하차 통계, 무정차 상태
├── MetroTrain ─────── 열차: 이동, 정차, 승하차 처리
│   └── (상속) BaseTrain ── 공통 속성 (ID, 색상, 노선)
│
├── Passenger ──────── 승객: 목적지 정보
├── SimulationClock ── 시뮬레이션 내부 시간
├── RushHourEvent ──── 러시아워 이벤트 (시간대, 가중치)
├── PassengerSpawner ─ 승객 생성 (확률 기반, 러시아워 반영)
│
└── DestinationPolicy (ABC) ── 목적지 선택 정책
    ├── RandomDestinationPolicy ──── 랜덤 목적지 (평상시)
    └── RushHourDestinationPolicy ── 업무지구 편향 (러시아워)

BottleneckAnalyzer ── 병목 감지 + 시나리오 비교 (Simulation을 외부에서 참조)

SubwaySystem ──── Pygame 실행, 입력 처리, 알림, 분석 호출
SubwayRenderer ── 지도, 열차, UI 패널 렌더링

StationOverloadError ── 역 과부하 예외 (65명 초과 시)
StationClosedError ──── 무정차 역 접근 예외


### 적용된 OOP 원칙

#### 상속 (Inheritance)
```python
class BaseTrain:
    """열차의 공통 속성: ID, 색상, 노선, 승객 리스트"""

class MetroTrain(BaseTrain):
    """이동, 정차, 승하차 로직 추가"""
```
`BaseTrain`이 공통 속성을 정의하고, 이를 상속받은 `MetroTrain`이 운행 로직을 확장

#### 다형성 (Polymorphism)
```python
class DestinationPolicy(ABC):
    @abstractmethod
    def choose_destination(self, origin_id, reachable_dests, clock, event): ...

class RandomDestinationPolicy(DestinationPolicy):
    def choose_destination(self, origin_id, reachable_dests, clock, event):
        return random.choice(candidates)

class RushHourDestinationPolicy(DestinationPolicy):
    def choose_destination(self, origin_id, reachable_dests, clock, event):
        # 러시아워 시 업무지구 가중치 적용
        return random.choices(candidates, weights=weights, k=1)[0]
```
동일한 `choose_destination()`으로, 특정 시간 이벤트에 따라 다른 목적지 선택 전략을 적용.
`DestinationPolicy`를 추상 베이스 클래스로 두어 인터페이스를 명시적으로 분리.

#### 매직 메소드 (Magic Methods)
```python
class Station:
    def __len__(self):      # len(station) → 대기 승객 수
    def __str__(self):      # str(station) → "강남역: 12명 대기"

class MetroTrain(BaseTrain):
    def __len__(self):      # len(train) → 탑승 승객 수

class SimulationClock:
    def __str__(self):      # str(clock) → "08:45"
```

#### 사용자 정의 예외 (Custom Exceptions)
```python
class StationOverloadError(Exception):
    #역 대기 인원 65명 초과 시 발생 → 경고 알림

class StationClosedError(Exception):
    #무정차 역에 승객 추가 시도 시 발생 → 인접 역으로 분산
```

시뮬레이션 시 이벤트 흐름을 제어 & 안내문 출력에 예외처리가 활용됩니다.

#### 책임 분리 (Separation of Concerns)
```
Simulation     → 순수 시뮬레이션 규칙 (Pygame 무관)
SubwaySystem   → 실행 루프, 입력 처리, 알림
SubwayRenderer → 화면 그리기
```
시뮬레이션 로직과 UI를 최대한 분리하고자 하였습니다.

---


## 파일 구조

```
subway_sim_more/
  __main__.py           패키지 실행 엔트리포인트
  main.py               직접 실행용 엔트리포인트
  simulation.py          시뮬레이션 상태와 규칙
  system.py              Pygame 실행, 입력, 알림
  renderer.py            UI 렌더링
  clock.py               시뮬레이션 내부 시간
  events.py              러시아워 이벤트
  destination_policy.py  목적지 선택 전략 (다형성)
  station.py             역 객체
  train.py               열차 객체 (상속)
  passenger.py           승객 객체
  spawner.py             승객 생성기
  analyzer.py            병목 감지 및 시나리오 분석
  data.py                역/노선/색상 데이터
  exceptions.py          사용자 정의 예외
```

---

## 의존성

- Python 3.10+
- Pygame (`pip install pygame`)