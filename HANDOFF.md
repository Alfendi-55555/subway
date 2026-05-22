# Subway Simulation 인수인계 문서

## 현재 프로젝트 개요

이 프로젝트는 지하철 노선도 기반 승객 흐름 시뮬레이션입니다. 역, 열차, 승객, 승객 생성기, 병목 분석기, Pygame UI가 상호작용하며, 무정차 처리와 병목 처방 시나리오 분석을 제공합니다.

프로젝트 가이드 기준으로는 단순 실행 프로그램보다 "현실 세계의 대중교통 혼잡 문제를 OOP 객체로 모델링한 시뮬레이션"이라는 스토리텔링을 강조하는 방향이 좋습니다.

## 실행 방식

권장 실행:

```powershell
python -m subway_sim_more
```

또는:

```powershell
python subway_sim_more\main.py
```

상대 import 오류가 날 수 있으므로 개별 모듈 파일을 직접 실행하는 방식은 권장하지 않습니다.

## 현재 주요 구조

```text
subway_sim_more/
  __main__.py          패키지 실행 엔트리포인트
  main.py              직접 실행용 엔트리포인트
  system.py            Pygame 화면, 입력, 알림, UI 실행 루프
  renderer.py          지도/열차/패널 UI 렌더링
  simulation.py        순수 시뮬레이션 상태와 규칙
  clock.py             내부 시뮬레이션 시간
  events.py            러시아워 이벤트
  destination_policy.py 목적지 선택 정책
  station.py           역 객체
  train.py             열차 객체
  passenger.py         승객 객체
  spawner.py           승객 생성기
  analyzer.py          병목 감지 및 시나리오 비교
  data.py              역/노선/색상 데이터
  exceptions.py        사용자 정의 예외
```

## 최근 리팩토링 요약

기존에 `system.py`와 `snapshot.py`에 중복되어 있던 시뮬레이션 로직을 `simulation.py`로 통합했습니다. 호환용으로 남겨두었던 `snapshot.py`는 외부 참조가 없는 것이 확인되어 제거했습니다.

현재 `Simulation`이 담당하는 것:

- 역, 노선, 열차, 승객 생성기 상태 보유
- 초기 승객 배치
- reachable/transfer 역 계산
- 시뮬레이션 복제 `clone()`
- 무정차 토글 및 승객 분산
- 인접 활성역/가까운 활성역 탐색
- 승객 생성 이벤트 처리
- redirect 처리
- `tick()`과 `fast_forward()`
- 시나리오용 무정차/열차 추가 적용
- 내부 시뮬레이션 시간 관리 객체 보유
- 러시아워 이벤트와 목적지 정책 연결

현재 `SubwaySystem`이 담당하는 것:

- Pygame 초기화
- 마우스 입력 처리
- 알림 표시
- 병목 분석 호출
- `Simulation` 업데이트 호출
- `SubwayRenderer` 호출

현재 `SubwayRenderer`가 담당하는 것:

- 지도 그리기
- 열차 그리기
- Stats/Alerts/Scenario/Controls 패널 그리기
- 현재 시뮬레이션 시간과 러시아워 상태 표시

## 중요한 주의사항

- GitHub 관련 작업은 하지 않습니다. 완전히 로컬 환경에서만 다룹니다.
- `main.py`의 fallback import는 사용자가 직접 관리한다고 했으므로, 불필요하게 건드리지 않는 것이 좋습니다.
- `system.py`의 `skip_station_ids`, `stations`, `trains` 등은 직접 속성이 아니라 `self.sim`으로 위임되는 property입니다. `self.skip_station_ids = ...`처럼 직접 할당하면 setter 오류가 납니다.
- Pygame 앱은 정상 실행 시 무한 루프에 들어가므로, 자동 검증 시에는 import/객체 생성/짧은 시뮬레이션 위주로 확인하는 것이 좋습니다.
- `train.py`의 승객 수 기반 지연은 `required_stop_time`을 실제 출발 조건에 사용해야 합니다. 현재는 `if self.stop_timer > required_stop_time:` 형태로 고쳐진 상태입니다.
- 무정차 분산 시 목적지 역에 도착한 승객은 대기열에 남지 않도록 `Station.add_passenger()`를 사용합니다.

## 검증 기록

최근 확인한 항목:

```powershell
Get-ChildItem subway_sim_more -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

통과.

```powershell
python -c "from subway_sim_more.system import SubwaySystem; app=SubwaySystem(); print(len(app.stations), len(app.trains), len(app.skip_station_ids))"
```

`15 3 0` 형태로 생성 확인.

```powershell
python -c "from subway_sim_more.simulation import Simulation; from subway_sim_more.analyzer import BottleneckAnalyzer; sim=Simulation.from_default_data(); print(BottleneckAnalyzer().run_scenario(sim, 's3', 1000).keys())"
```

`results`, `scores`, `best` 구조 확인.

추가로 최근 확인한 항목:

```powershell
python -c "from subway_sim_more.system import SubwaySystem; app=SubwaySystem(); print(type(app.renderer).__name__, len(app.stations), len(app.trains))"
```

`SubwayRenderer 15 3` 형태로 renderer 연결 확인.

## 현재 구현 완료 기능

### 러시아워 + 목적지 편향

구현 완료:

- `clock.py`: `SimulationClock`
  - 기본 시작 시각은 07:00
  - 기본 배율은 현실 1초 = 시뮬레이션 2분
- `events.py`: `RushHourEvent`
  - 출근 러시아워: 07:30-09:30
  - 출발역 가중치
  - 업무지구 목적지 가중치
- `destination_policy.py`
  - `RandomDestinationPolicy`
  - `RushHourDestinationPolicy`
- `spawner.py`
  - 러시아워 global multiplier 반영
  - 출발역 weight 보정
  - 목적지 정책으로 `Passenger` 생성
- `system.py`/`renderer.py`
  - Stats 패널에 현재 시각과 이벤트 상태 표시

러시아워 목적지 선호 역:

```text
강남(s1), 교대(s2), 고속터미널(s3), 양재(s8)
```

### 병목/시나리오 평가

사용자 수정으로 반영된 내용:

- `train.py`: 대기 승객 수에 비례한 정차 지연
- `analyzer.py`: `total_boarded`, `overloaded_stations`, `train_progress` 기반 평가
- `system.py`/`renderer.py`: 변경된 시나리오 결과 키 표시

주의: `train.py`에서 `required_stop_time`을 계산만 하고 고정값 `1500`을 쓰면 지연이 적용되지 않습니다. 현재는 수정되어 있습니다.

### 렌더러 분리

`system.py`의 `_draw_*` 메서드를 `renderer.py`의 `SubwayRenderer`로 분리했습니다.

현재 구조:

```text
Simulation      시뮬레이션 규칙
SubwaySystem    실행 흐름, 입력, 알림, 분석 호출
SubwayRenderer  화면 그리기
```

## 다음 기능 기획

남은/고려 중인 기능:

1. 사용자 직접 열차 추가
2. 날씨 대신 다른 이벤트 추가 여부 검토
3. 폴더 구조 정리
4. README/발표자료/UML 정리

### 사용자 직접 열차 추가

러시아워 이후 병목이 생겨도 현재 사용자가 직접 할 수 있는 조작은 무정차 토글뿐입니다. 시나리오 분석에는 `C: 열차 추가`가 있으므로, 실제 상호작용에도 열차 추가를 넣는 것이 자연스럽습니다.

추천 설계:

```text
좌클릭: 무정차 토글
우클릭: 시나리오 분석
Shift + 좌클릭 또는 중클릭: 해당 역이 포함된 노선에 열차 추가
```

구현 후보:

- `Simulation.apply_extra_train(station_id)`를 실제 조작에도 재사용
- 무제한 추가를 막기 위해 `MAX_EXTRA_TRAINS`와 `extra_train_count` 추가
- `clone()`에도 `extra_train_count` 복사
- `renderer.py`의 Controls 안내문 수정
- `system.py`의 마우스 이벤트 처리 수정

추천 제한:

```text
전체 추가 열차 최대 3대
또는 노선당 추가 열차 1대
```

구현 규모는 작음~중간입니다. 수정 예상 파일은 `simulation.py`, `system.py`, `renderer.py`입니다.

### 러시아워 이벤트 기록

현재 승객 목적지는 러시아워 중 업무지구 역으로 편향되도록 구현되어 있습니다.

기본 방향:

- 일반 시간대: 목적지 랜덤
- 출근 시간대: 주거/외곽 역에서 업무지구로 향하는 목적지 편향
- 퇴근 시간대: 업무지구에서 주거/외곽 역으로 향하는 목적지 편향

초기 구현은 단순 multiplier 방식으로 시작할 수 있습니다.

예:

```text
07:30-09:30 출근 러시아워
강남, 교대, 고속터미널, 양재 목적지 선호도 증가

18:00-20:00 퇴근 러시아워
중심 업무지구 출발 승객 증가
외곽/주거지 목적지 선호도 증가
```

### 날씨 이벤트 또는 대체 이벤트

날씨 이벤트는 아직 보류 상태입니다. 구현한다면 전체 승객 유입량에 영향을 주는 전역 이벤트로 설계할 수 있습니다.

예:

```text
맑음: x1.0
비: x1.3
폭우: x1.6
눈: x1.8
```

초기에는 랜덤 날씨 또는 고정 날씨 상태를 두고, `PassengerSpawner`의 전체 생성량에 multiplier를 적용하면 됩니다.

### 목적지 정책

현재 클래스:

```text
DestinationPolicy
  RandomDestinationPolicy
  RushHourDestinationPolicy
```

같은 메서드로 목적지를 고르되, 시간대/이벤트에 따라 다른 정책 객체를 사용하는 식이라 다형성 설명에 좋습니다.

예상 메서드:

```python
choose_destination(origin_id, reachable_dests, context)
```

여기서 `context`에는 현재 시각, 활성 이벤트, 날씨, 역 정보 등이 들어갈 수 있습니다.

## 앞으로 추천 구현 순서

기능 구현과 폴더 정리를 한 번에 하면 import 오류 추적이 어려워질 수 있으므로, 기능 먼저 마무리하고 구조 정리는 나중에 하는 것이 안전합니다.

추천 순서:

1. 사용자 직접 열차 추가 기능 구현
2. 파라미터 최종 튜닝
3. README 정리
4. 발표용 UML/객체 관계도 작성
5. 이후 폴더 구조 정리
   - 기능 안정화 후 하위 폴더로 이동

## 폴더 구조 정리안

기능이 안정화된 뒤 다음처럼 정리하는 것을 추천합니다.

```text
subway_sim_more/
  __init__.py
  __main__.py
  main.py

  core/
    simulation.py
    clock.py
    events.py
    destination_policy.py

  domain/
    station.py
    train.py
    passenger.py
    exceptions.py

  services/
    spawner.py
    analyzer.py

  ui/
    system.py

  data/
    network.py
```

단, 폴더 이동은 import 경로를 대량 수정해야 하므로 별도 단계로 진행하는 것이 좋습니다.

## 구현 규모 메모

러시아워 + 날씨 + 목적지 편향까지는 중간 규모 작업입니다.

예상 변경 파일:

- 새 파일: `clock.py`, `events.py`, `destination_policy.py`
- 수정 파일: `spawner.py`, `simulation.py`, `system.py`
- 선택 수정: `station.py`, `data.py`

폴더 구조 정리까지 포함하면 중간 이상 규모가 됩니다. 기능 구현과 폴더 이동은 분리해서 진행하는 것이 안전합니다.
