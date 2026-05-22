# 코드 개선 사항 정리

> **작성일**: 2026-05-22
> **목적**: 제출 직전 코드 리뷰 및 평가 대비
> **요약**: 사용자가 체감하던 핵심 버그 4건 + 코드 품질 개선 6건 + 데드 코드 1건 정리. 평가 기준(필수 요구사항·OOP 아키텍처·OOP 문법)을 모두 충족하며, 평가자가 코드를 정독했을 때 잡힐 만한 인상점수 항목까지 함께 다듬었다.

---

## 1. 핵심 버그 수정 (체감 가능)

### 1.1 무정차 처방 시 승객 처리 누락

**문제**: B역이 무정차로 전환됐을 때 다음 케이스들이 처리되지 않았다.
- 인접역(A)에서 대기 중이고 목적지가 B인 승객 → 열차에 탑승되지만 B를 통과해도 내리지 못해 **영구히 갇힘**
- 이미 열차에 타고 있고 목적지가 B인 승객 → 같은 운명
- 새로 생성되는 승객이 여전히 B를 목적지로 선택 가능

**수정**: 세 갈래로 처리.
- **옵션 1(a)** [`destination_policy.py`]: `choose_destination`에 `skip_station_ids` 파라미터 추가. 후보에서 skipped 역 제외.
- **옵션 1(b)** [`train.py`]: `handle_boarding`에서 destination이 skipped인 대기 승객은 승차 차단.
- **옵션 3** [`train.py`]: 무정차 역 통과 시 destination=그 역인 탑승객 강제 하차.

**영향 파일**: `destination_policy.py`, `spawner.py`, `simulation.py`, `train.py`

**Q&A 방어 답변**:
> "무정차 전환 시점에 그 역에 있던 사람은 인접 활성역으로 분산되고, 열차에 타고 있던 사람은 무정차 역을 지나칠 때 강제 하차됩니다 (현실의 '다음역에서 내리세요' 안내와 같음). 전환 이후 새로 생성되는 승객은 애초에 무정차 역을 목적지로 선택하지 않습니다."

---

### 1.2 끝쪽 역에서 "열차 추가" 처방이 반대 방향으로 떠나감

**문제**: 노선 첫 역(압구정 s12, 강남 s1)에 열차 추가 처방을 내리면, `start_index = max(0, station_index - 1) = 0`이 되어 새 열차가 타겟 역 자체에서 출발해 정방향(반대편)으로 가버린다. 병목 해소 효과 없음.

**수정** [`simulation.py:apply_extra_train`]: 노선 첫 역이면 `start_index=1, direction=-1`로, 그 외에는 기존대로.
```python
if station_index == 0:
    start_index = 1
    direction = -1
else:
    start_index = station_index - 1
    direction = 1
```

**부수 영향**: 시나리오 분석의 "열차 추가" 점수가 끝쪽 역에서도 정상 측정됨. 이전엔 새 열차가 30초 동안 타겟을 처리하지 않아 처방이 부당하게 낮게 평가되었다.

---

### 1.3 시나리오 분석의 RNG 흐름

**문제**:
- `random.seed(42)`가 `setup_fn` **뒤**에 있어 "무정차 분산"의 승객 재분배가 비결정적이었음 (직전 시나리오의 fast_forward가 남긴 random 상태에 의존).
- 글로벌 `random` 모듈을 그대로 갈아엎어, 분석을 한 번 누르면 라이브 시뮬레이션의 승객 생성 패턴이 분석 안 누른 평행우주와 달라짐.

**수정** [`analyzer.py:run_scenario`]:
- `random.seed(42)`를 `setup_fn` 앞으로 이동
- 분석 전후로 `random.getstate()` / `random.setstate(saved_state)`로 백업/복원
- (덤) 결과 집계 블록을 for 루프 안으로 정렬 (이전엔 마지막 시나리오 결과만 기록될 위험 — 단, 들여쓰기 수정 과정에서 한 차례 만든 buggy 중간 상태를 후속 edit으로 수습한 것)

**Q&A 방어 답변**:
> "세 시나리오는 동일한 난수 시작 상태에서 출발하여, 처방의 효과만으로 결과가 갈리도록 했습니다. 분석은 라이브 시뮬레이션의 random 상태를 변형시키지 않습니다."

---

### 1.4 초기 3대 열차의 시각적 정지

**문제**: 시뮬레이션 시작 직후 약 2초 동안 열차들이 첫 역에서 정지한 채 머묾. 게다가 이 정차 시간 동안 **승객을 한 명도 태우지 않음** (handle_boarding은 "이동 후 도착" 시점에만 호출되기 때문).

**수정** [`simulation.py:from_default_data`]: 초기 승객 배치 후, 각 열차의 첫 역에서 1회 boarding을 수행하고 `is_stopped=False`로 풀어준다.
```python
for train in trains:
    start_station = stations[train.route_ids[train.current_idx]]
    train.handle_boarding(start_station, sim.skip_station_ids)
    train.is_stopped = False
```

**효과**:
- 시작 즉시 부드러운 출발 → 시연 첫인상이 자연스러움
- 첫 사이클부터 출발역 초기 승객이 처리됨

---

## 2. 잠재 문제 정리 (코드 품질 / 리뷰 방어)

### 2.1 초기 승객 일부의 "투명 증발"

**문제**: `_build_reachable`은 출발역 자신도 reachable 후보에 포함한다. `seed_initial_passengers`에서 `random.choice`가 출발역을 뽑으면 `add_passenger`의 분기에서 조용히 삭제됨. 초기 승객의 약 10%가 소실.

**수정** [`station.py:add_passengers`]: 후보에서 자기 자신 제외.
```python
candidates = [dest for dest in reachable_dests if dest != self.id]
```

---

### 2.2 `apply_extra_train`이 route 리스트를 참조 공유

**문제**: `MetroTrain(..., route, ...)`이 `self.lines[line_index]`와 같은 객체를 공유. 노선 데이터 mutation에 취약. `clone()`은 정상적으로 `route_ids[:]` 슬라이스 복사를 하는데 이 부분만 다름.

**수정** [`simulation.py:apply_extra_train`]: `route` → `route[:]`

---

### 2.3 추가 열차의 시각적 1.5초 정지

**문제**: `apply_extra_train`으로 추가된 열차도 `is_stopped=True`로 출생. 중간 위치에서 1.5초 동안 정지 후 출발.

**수정** [`simulation.py:apply_extra_train`]: `extra.is_stopped = False` 추가.

---

### 2.4 `redirect_to_adjacent`의 조기 종료

**문제**: 첫 인접역의 `choose_destination`이 `None`을 반환하면 다른 인접역을 시도하지 않고 즉시 `return False`.

**수정** [`simulation.py:redirect_to_adjacent`]: `return False` → `continue`.

---

### 2.5 렌더러가 시스템 상태를 직접 수정

**문제**: `renderer._draw_alerts`가 `system.alerts`의 만료 정리를 수행. "렌더러는 그리기만 한다"는 책임 분리 원칙 위반.

**수정**:
- [`renderer.py`]: 해당 줄 삭제
- [`system.py`]: `_prune_alerts()` 메서드 추가, `run()` 메인 루프에서 호출

**Q&A 방어 답변**:
> "3-Layer 책임 분리: Simulation은 순수 도메인 규칙, SubwaySystem은 실행/입력/알림 생명주기 관리, SubwayRenderer는 화면 그리기만 담당하여 상태를 변경하지 않습니다."

---

### 2.6 `handle_boarding`의 `waiting_passengers` 직접 대입

**문제**: 외부 클라이언트(Train)가 Station의 내부 리스트를 직접 갈아 끼움. 캡슐화 위반.

**수정**:
- [`station.py`]: `set_waiting(passengers)` 메서드 추가. 리스트 교체 + `max_waiting` 자동 갱신.
- [`train.py`]: 직접 대입 → `station.set_waiting(...)` 호출.

---

## 3. 데드 코드 제거

### 3.1 `snapshot.py` 삭제

**문제**: 빈 `SimSnapshot(Simulation)` 클래스만 호환용으로 남아 있었음. 외부 참조 0건 확인. 평가자에게 "왜 빈 클래스가 있지?" 인상을 줄 위험.

**수정**: 파일 삭제 + `HANDOFF.md`에서 관련 언급 정리.

---

## 4. 변경 파일 인덱스

| 파일 | 변경 사유 |
|---|---|
| `analyzer.py` | 1.3 (RNG 흐름) |
| `destination_policy.py` | 1.1 (skip 후보 제외) |
| `spawner.py` | 1.1 (skip_station_ids 전달) |
| `simulation.py` | 1.1, 1.2, 1.4, 2.2, 2.3, 2.4 |
| `train.py` | 1.1, 2.6 |
| `station.py` | 2.1, 2.6 |
| `renderer.py` | 2.5 |
| `system.py` | 2.5 |
| `snapshot.py` | 3.1 (삭제) |
| `HANDOFF.md` | 3.1 (참조 정리) |

---

## 5. 미해결 / 사용자가 직접 정리 예정

- `data.py:36` LINE_NAMES 주석 (실제로는 `system.py`에서 사용 중이라 "쓰이고 있지 않다"는 주석이 거짓)
- `exceptions.py:1` 첫 줄 오타 (`#t사용자 예외 처리` → `#사용자 예외 처리`)

---

## 6. 제출 전 남은 작업

- [ ] 발표용 자료 (PPT/PDF) — UML 다이어그램 포함 권장
- [ ] 팀원별 분담 명세서 — README 하단 또는 별도 파일
- [ ] 위 5번 주석 정리
- [ ] 발표 리허설 (시연 흐름 + Q&A 대비)

---

## 부록 — 평가기준 충족 현황

| 항목 | 기준 | 현재 상태 |
|---|---|---|
| 클래스 개수 | ≥ 3개 | 13개+ ✅ |
| 상속/다형성 | ≥ 1 | `BaseTrain → MetroTrain`, `DestinationPolicy(ABC) → Random/RushHour` (이중 적용) ✅ |
| 매직 메소드 | `__init__` 외 2개+ | `__str__`, `__len__` (총 5회 활용) ✅ |
| 사용자 정의 예외 | ≥ 1 | `StationOverloadError`, `StationClosedError` — 흐름 제어용으로 활용 ✅ |
