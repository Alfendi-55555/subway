# MetroSim — 지하철 혼잡 처방 시뮬레이터

> **"출근길 강남역. 32명이 한 번에 몰려들었다. 열차 한 대로 부족하다면, 우리는 무엇을 할 수 있을까?"**

매일 수백만이 통과하는 지하철. 한 역의 병목은 인접 역까지 번지고, 시민의 통근 시간은 30분에서 50분으로 늘어납니다.
**MetroSim**은 이 현실 문제를 객체로 모델링하고, "현상유지 vs 무정차 vs 열차추가" 세 가지 처방을 *평행우주에서 동시에 돌려* 효과를 비교하는 정책 시뮬레이터입니다.

---

## 목차

1. [세계관 — 우리가 시뮬레이션하는 문제](#1-세계관--우리가-시뮬레이션하는-문제)
2. [실행 방법](#2-실행-방법)
3. [시나리오 흐름](#3-시나리오-흐름)
4. [OOP 시스템 아키텍처](#4-oop-시스템-아키텍처)
5. [OOP 4대 특성 적용](#5-oop-4대-특성-적용)
6. [OOP 문법 활용](#6-oop-문법-활용)
7. [노선도와 데이터](#7-노선도와-데이터)
8. [파일 구조](#8-파일-구조)
9. [의존성](#9-의존성)

---

## 1. 세계관 — 우리가 시뮬레이션하는 문제

### 문제 정의
출근 시간 강남·교대·고속터미널·양재 일대의 업무지구로 승객이 쏠립니다. 특정 역의 대기 인원이 임계점을 넘으면 열차의 정차 시간이 길어지고, 지연은 인접 역으로 전파됩니다. 운영자는 두 가지 처방을 선택할 수 있습니다 — **무정차 운행**으로 한 역을 건너뛰거나, **열차 증편**으로 노선 흐름을 늘리는 방법입니다.

하지만 "어느 쪽이 더 효과적인가?"는 직관만으로 판단할 수 없습니다. 시간대, 노선 위상, 인접 역의 여유 용량이 모두 얽혀 있기 때문입니다.

### 우리의 해결책
MetroSim은 모든 객체를 동일 시드의 평행우주로 복제해, **세 처방을 동시에 30초간 돌리고 결과를 정량 점수로 비교**합니다.

```
점수 = 0.5 × (정규화된 처리량)
     + 0.4 × (정규화된 노선 흐름)
     − 0.3 × (과부하 역 수)
```

직관에 의존하지 않고, *수치로* 처방을 선택할 수 있는 분석 도구입니다.

---

## 2. 실행 방법

```powershell
python -m subway_sim_more
```
또는 `main.py` 파일을 직접 실행합니다.

### 조작법

| 입력 | 동작 |
|---|---|
| **좌클릭** (역) | 무정차 토글 — 해당 역을 건너뛰고 대기 승객을 인접 역으로 분산 |
| **우클릭** (역) | 시나리오 분석 — 1시간 고속 시뮬레이션으로 3가지 처방 비교 |
| **[적용] 버튼** | 분석 결과에서 추천 처방을 실제 시뮬레이션에 적용 (열차 추가는 최대 3대) |

---

## 3. 시나리오 흐름

```
07:00  시뮬레이션 시작. 역마다 승객이 조금씩 대기.
          ↓
07:30  출근 러시아워 돌입.
        - 업무지구(강남/교대/고터/양재)로 승객 목적지 편향 (3~4배 가중치)
        - 외곽·주거지 역에서 출발 승객 증가 (1.5~1.8배 가중치)
          ↓
       병목 감지! "고속터미널역 32명 대기" 경고 발생.
          ↓
       우클릭 → 시나리오 분석:
        ┌──────────┬─────────┬─────────┬───────┐
        │ 처방     │ 처리량  │ 흐름    │ 점수  │
        ├──────────┼─────────┼─────────┼───────┤
        │ 현상유지 │   180명 │  12.3   │ 0.62  │
        │ 무정차   │   210명 │  14.8   │ 0.78  │
        │ 열차추가 │   245명 │  16.1   │ 0.91  │← 추천
        └──────────┴─────────┴─────────┴───────┘
          ↓
       [적용] 버튼 클릭 → 추천 처방이 즉시 라이브에 반영
          ↓
       처방 효과를 실시간으로 확인
```

---

## 4. OOP 시스템 아키텍처

### 4.1 3-Layer 책임 분리

```
┌─────────────────────────────────────────────────────┐
│  표현/실행 레이어 (Pygame 의존)                        │
│  ───────────────────────                            │
│  SubwaySystem   ── 실행 루프, 입력, 알림 수명주기     │
│  SubwayRenderer ── 지도, 열차, UI 그리기만 (상태 X)   │
└──────────────────────┬──────────────────────────────┘
                       ▼ (uses)
┌─────────────────────────────────────────────────────┐
│  분석 레이어                                          │
│  ──────────                                          │
│  BottleneckAnalyzer                                  │
│   ├ detect()       — 30명 이상 역 자동 감지            │
│   └ run_scenario() — clone × 3 평행 시뮬레이션         │
└──────────────────────┬──────────────────────────────┘
                       ▼ (uses)
┌─────────────────────────────────────────────────────┐
│  도메인 레이어 (Pygame 무관 — 헤드리스 실행 가능)        │
│  ─────────────────────────────                       │
│  Simulation                                          │
│   ├── Station[]            (Passenger[]를 보유)       │
│   ├── MetroTrain[]         (Passenger[]를 보유)       │
│   ├── SimulationClock      (가상 시간, 120× 배율)     │
│   ├── RushHourEvent        (시간대별 가중치)          │
│   ├── PassengerSpawner     (확률적 생성)             │
│   └── DestinationPolicy    (전략 패턴 ABC)           │
│        ├ RandomDestinationPolicy                     │
│        └ RushHourDestinationPolicy                   │
└─────────────────────────────────────────────────────┘
       ▲
       │ (raises / catches)
┌──────┴──────────────────────────┐
│  횡단 관심사                     │
│  StationOverloadError           │
│  StationClosedError             │
└─────────────────────────────────┘
```

**핵심 설계 원칙**: 도메인 레이어는 Pygame을 import하지 않습니다. 덕분에 `BottleneckAnalyzer`가 `simulation.clone()`으로 **헤드리스 평행 시뮬레이션**을 돌릴 수 있습니다.

### 4.2 클래스 카테고리

모든 클래스를 책임 영역으로 분류하면 다음과 같습니다.

| 카테고리 | 책임 | 클래스 |
|---|---|---|
| **도메인 핵심** | 시뮬레이션 상태와 규칙 | `Simulation`, `Station`, `MetroTrain`, `Passenger`, `BaseTrain` |
| **시간·이벤트** | 가상 시간 흐름, 시간대별 이벤트 | `SimulationClock`, `RushHourEvent` |
| **전략(추상화)** | 시간대별 목적지 선택 알고리즘 | `DestinationPolicy`(ABC), `RandomDestinationPolicy`, `RushHourDestinationPolicy` |
| **행위 서비스** | 승객 생성, 병목 감지·분석 | `PassengerSpawner`, `BottleneckAnalyzer` |
| **표현·실행** | 화면, 입력, 알림 오케스트레이션 | `SubwaySystem`, `SubwayRenderer` |
| **횡단 관심사** | 예외 (흐름 제어용) | `StationOverloadError`, `StationClosedError` |

### 4.3 객체 간 핵심 상호작용

| 시나리오 | 호출 체인 |
|---|---|
| **승객 생성** | `Simulation.spawn_passengers` → `PassengerSpawner.tick` → `DestinationPolicy.choose_destination` → `Station.add_passenger_to` |
| **무정차역 충돌** | `Station.add_passenger` *raises* `StationClosedError` → `Simulation.redirect_to_adjacent` (인접 역 재시도) |
| **과부하 경보** | `Station.add_passenger` *raises* `StationOverloadError` → spawner가 alert로 변환 → `SubwaySystem.add_alert` |
| **열차 운행** | `Simulation.update` → `MetroTrain.update_logic` → (정차 만료) → `handle_boarding` → `Station.record_boarding` |
| **시나리오 분석** | 우클릭 → `SubwaySystem.run_analysis` → `BottleneckAnalyzer.run_scenario` → `Simulation.clone × 3` + `fast_forward` → 점수 비교 |
| **처방 적용** | [적용] → `SubwaySystem._apply_scenario` → `Simulation.toggle_skip` / `add_user_train` |

---

## 5. OOP 4대 특성 적용

각 특성이 코드 어디에서 어떻게 실현되는지 명시합니다.

### 5.1 추상화 (Abstraction)
**핵심**: 인터페이스만 노출하고 구현 세부를 숨김.

```python
class DestinationPolicy(ABC):
    @abstractmethod
    def choose_destination(self, origin_id, reachable_dests, ...) -> str | None: ...
```
`PassengerSpawner`와 `Simulation`은 구체 정책을 모른 채 `choose_destination`만 호출합니다. 정책을 새로 추가해도(예: `WeekendDestinationPolicy`) 호출부를 수정할 필요가 없습니다.

### 5.2 캡슐화 (Encapsulation)
**핵심**: 객체의 내부 상태는 그 객체의 메서드를 통해서만 변경.

```python
class Station:
    def set_waiting(self, passengers: list[Passenger]) -> None:
        """대기열 교체. max_waiting 갱신을 자동 보장."""
        self.waiting_passengers = passengers
        self.max_waiting = max(self.max_waiting, len(self))
```
`MetroTrain`은 `Station.waiting_passengers`를 직접 갈아 끼우지 않고 `set_waiting()`을 통해 변경합니다. 통계 불변식(`max_waiting`)이 항상 일관되게 유지됩니다.

### 5.3 상속 (Inheritance)
**핵심**: 공통 속성·동작을 부모에 정의하고 자식이 확장.

```python
class BaseTrain:
    """공통 속성: ID, 색상, 노선, 승객 리스트"""
    def __init__(self, id, color, route_ids):
        self.id = id; self.color = color
        self.route_ids = route_ids
        self.passengers = []

class MetroTrain(BaseTrain):
    """운행 로직 추가"""
    def __init__(self, id, color, route_ids, start_index, direction):
        super().__init__(id, color, route_ids)
        # 이동, 정차, 승하차 상태 추가
```
또한 `DestinationPolicy → Random/RushHour` 계층에서도 상속이 활용됩니다 (이중 적용).

### 5.4 다형성 (Polymorphism)
**핵심**: 동일한 인터페이스가 객체 종류에 따라 다른 동작.

```python
class RandomDestinationPolicy(DestinationPolicy):
    def choose_destination(self, ...):
        return random.choice(candidates)              # 균등 분포

class RushHourDestinationPolicy(DestinationPolicy):
    def choose_destination(self, ...):
        if event.is_active(clock):
            weights = [event.destination_multiplier(s, clock) for s in candidates]
            return random.choices(candidates, weights=weights, k=1)[0]  # 가중 분포
        return random.choice(candidates)
```
동일한 `choose_destination()` 호출이 정책 객체에 따라 *균등 분포* 또는 *업무지구 편향 분포*로 동작합니다 — **전략 패턴(Strategy Pattern)**의 정공법 구현입니다.

---

## 6. OOP 문법 활용

### 6.1 매직 메소드 (Magic Methods)

```python
# Station
def __len__(self) -> int:           # len(station) → 대기 승객 수
    return len(self.waiting_passengers)
def __str__(self) -> str:           # str(station) → "강남역: 12명 대기"
    return f"{self.name}역: {len(self)}명 대기"

# MetroTrain
def __len__(self) -> int:           # len(train) → 탑승 승객 수
    return len(self.passengers)

# SimulationClock
def __str__(self) -> str:           # str(clock) → "08:45"
    ...

# Passenger
def __str__(self) -> str:           # str(passenger) → "Passenger(to=s3)"
```

`__init__`을 제외하고 **`__str__`, `__len__` 두 종류가 총 5회** 활용됩니다.

### 6.2 사용자 정의 예외 (Custom Exceptions)

```python
class StationOverloadError(Exception):
    """역 대기 인원 65명 초과 → 경고 알림 발행"""

class StationClosedError(Exception):
    """무정차 역에 승객 추가 시도 → 인접 역으로 redirect"""
```

**단순 에러 처리가 아닌, 시뮬레이션 이벤트 흐름 제어용**으로 활용합니다:
- `StationClosedError`가 잡히면 `Simulation.redirect_to_adjacent`가 자동 호출되어 인접 활성역에 승객을 다시 시도합니다.
- `StationOverloadError`는 spawner가 잡아 alert 이벤트로 변환, UI에 경고를 표시합니다.

---

## 7. 노선도와 데이터

```
                    압구정(s12)
                      │
                    잠원(s13)
                      │
강남 ── 교대 ── 고속터미널 ── 반포 ── 논현 ── 신사     ← 청색선
                 │           │
               남부터미널     │
                 │           │
교대 ── 남부터미널 ── 양재 ── 매봉 ── 도곡 ── 대치     ← 녹색선
                      │
                    학여울(s14)
                      │
                    대청(s15)
                                                       ↕ 주황선
압구정 ── 잠원 ── 반포 ── 양재 ── 학여울 ── 대청
```

- **15개 역, 3개 노선** (청색·녹색·주황)
- **환승역**: 교대(s2), 반포(s4), 양재(s8)
- 역마다 `weight`(0.1~3.0)를 두어 평상시 승객 발생 빈도를 차등화
- 러시아워 시 추가 가중치 (출발지 1.5~1.8×, 업무지구 도착지 3~4×)

---

## 8. 파일 구조

```
subway_sim_more/
  __main__.py            패키지 실행 엔트리포인트
  main.py                직접 실행용 엔트리포인트

  # 도메인 레이어 (Pygame 무관)
  simulation.py          전체 시뮬레이션 상태와 규칙
  station.py             역 객체
  train.py               열차 객체 (BaseTrain → MetroTrain 상속)
  passenger.py           승객 객체
  clock.py               가상 시간
  events.py              러시아워 이벤트
  destination_policy.py  목적지 선택 전략 (ABC + 2개 구현)
  spawner.py             승객 생성기
  exceptions.py          사용자 정의 예외
  data.py                역/노선/색상 데이터

  # 분석 레이어
  analyzer.py            병목 감지 + 시나리오 비교

  # 표현/실행 레이어
  system.py              실행 루프, 입력, 알림
  renderer.py            화면 그리기

  # 문서
  README.md              사용자용 안내
  CHANGES.md             최근 코드 개선 내역
  HANDOFF.md             내부 작업 메모
```

---

## 9. 의존성

- **Python 3.10+** (`int | None` 같은 PEP 604 union 문법 사용)
- **Pygame** (`pip install pygame`)

---

## 부록 — 평가기준 충족 현황

| 기준 | 요구 | 충족 |
|---|---|---|
| 클래스 개수 | ≥ 3개 상호작용 | 13개+ |
| 상속 / 다형성 | ≥ 1 의미 있는 적용 | `BaseTrain → MetroTrain` + `DestinationPolicy → Random/RushHour` (이중) |
| 매직 메소드 | `__init__` 외 2개 이상 | `__str__`, `__len__` (총 5회) |
| 사용자 정의 예외 | ≥ 1 | 2개 (모두 흐름 제어용) |
| OOP 4대 특성 | — | 추상화·캡슐화·상속·다형성 모두 명시적 적용 (§5) |
