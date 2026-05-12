import pygame
import random
import sys

# ---------------------------------------------------------
# 1. OOP 아키텍처 및 예외 정의
# ---------------------------------------------------------

class StationOverloadError(Exception):
    """사용자 정의 예외: 특정 역의 인원이 임계값을 넘으면 발생"""
    def __init__(self, name, count):
        super().__init__(f"{name}역 과부하: {count}명 대기!")

class StationClosedError(Exception):
    """사용자 정의 예외: 무정차(폐쇄) 역에 승객 추가 시도 시 발생"""
    def __init__(self, name):
        super().__init__(f"{name}역은 현재 무정차 상태입니다.")

class Passenger:
    """승객 객체: 목적지 데이터를 가짐"""
    def __init__(self, destination_id):
        self.destination_id = destination_id

class Station:
    """
    지하철역 클래스: 대기열 및 누적 통계 관리
    
    weight: 승객 유입 가중치 (환승역은 높게 설정)
    is_skipped: 무정차(폐쇄) 여부
    max_waiting: 시뮬 중 최대 대기 인원 (시나리오 분석용)
    """
    OVERLOAD_THRESHOLD = 50  # 과부하 기준 인원

    def __init__(self, id, name, x, y, weight=1.0):
        self.id = id
        self.name = name
        self.x, self.y = x, y
        self.weight = weight          # 승객 유입 가중치
        self.waiting_passengers = []
        self.total_boarded = 0
        self.total_alighted = 0
        self.max_waiting = 0          # 시나리오 분석용 최대 대기 기록
        self.is_skipped = False       # 무정차 여부

    def __len__(self):
        """매직 메소드: len(station)으로 대기자 수 확인"""
        return len(self.waiting_passengers)

    def __str__(self):
        """매직 메소드: 역 상태 출력"""
        status = " [무정차]" if self.is_skipped else ""
        return f"{self.name}역: {len(self)}명 대기 중{status}"

    def add_passengers(self, count, reachable_dests):
        """
        승객 유입 로직.
        무정차 역이면 StationClosedError,
        50명 초과면 StationOverloadError 발생.
        """
        if self.is_skipped:
            raise StationClosedError(self.name)

        for _ in range(count):
            dest = random.choice(reachable_dests)
            if dest != self.id:
                self.waiting_passengers.append(Passenger(dest))

        # 최대 대기 인원 갱신 (시나리오 분석용)
        if len(self) > self.max_waiting:
            self.max_waiting = len(self)

        if len(self) > self.OVERLOAD_THRESHOLD:
            raise StationOverloadError(self.name, len(self))


class BaseTrain:
    """부모 클래스: 열차의 공통 속성 정의"""
    def __init__(self, id, color, route_ids):
        self.id = id
        self.color = color
        self.route_ids = route_ids
        self.passengers = []  # AttributeError 방지를 위해 부모에서 생성

class MetroTrain(BaseTrain):
    """
    자식 클래스: 실제 운행 및 다형성 탑승 로직 구현
    무정차 역은 통과하고, smart boarding으로 노선 내 승객만 탑승.
    """
    CAPACITY = 50

    def __init__(self, id, color, route_ids, start_index, direction):
        super().__init__(id, color, route_ids)
        self.current_idx = start_index
        self.direction = direction
        self.target_idx = start_index + direction
        self.progress = 0.0
        self.is_stopped = True
        self.stop_timer = 0

    def update_logic(self, dt, stations_dict, skip_station_ids):
        """이동 및 정차 로직. 무정차 역은 통과."""
        if self.is_stopped:
            self.stop_timer += dt
            if self.stop_timer > 1500:  # 1.5초 정차
                self.is_stopped = False
                self.stop_timer = 0
                self.set_next_target()
        else:
            self.progress += dt / 2000.0
            if self.progress >= 1.0:
                self.progress = 0.0
                self.current_idx = self.target_idx
                cur_sid = self.route_ids[self.current_idx]

                if cur_sid in skip_station_ids:
                    # 무정차 통과: 정차 없이 바로 다음 역으로
                    self.set_next_target()
                else:
                    self.is_stopped = True
                    self.handle_boarding(stations_dict[cur_sid])

    def set_next_target(self):
        """방향 전환 로직"""
        next_val = self.current_idx + self.direction
        if next_val >= len(self.route_ids) or next_val < 0:
            self.direction *= -1
        self.target_idx = self.current_idx + self.direction

    def handle_boarding(self, station):
        """
        다형성: 역과 열차 간의 데이터 상호작용.
        하차 → 노선 내 목적지 승객만 승차.
        """
        # 하차
        initial_count = len(self.passengers)
        self.passengers = [p for p in self.passengers if p.destination_id != station.id]
        station.total_alighted += (initial_count - len(self.passengers))

        # 승차: 해당 노선 목적지 승객만
        space = self.CAPACITY - len(self.passengers)
        can_board = [p for p in station.waiting_passengers if p.destination_id in self.route_ids]
        cannot_board = [p for p in station.waiting_passengers if p.destination_id not in self.route_ids]

        boarding = can_board[:space]
        station.waiting_passengers = can_board[space:] + cannot_board
        self.passengers.extend(boarding)
        station.total_boarded += len(boarding)


# ---------------------------------------------------------
# 2. 시뮬레이션 스냅샷 (pygame 없는 경량 복사본)
# ---------------------------------------------------------

class SimSnapshot:
    """
    고속 시뮬 전용 경량 시스템 복사본.
    pygame.Surface 등 렌더링 객체를 전혀 갖지 않아
    deepcopy 없이 시나리오 비교 시뮬이 가능합니다.
    fast_forward / _apply_skip / _apply_extra_train 메서드만 보유.
    """

    def fast_forward(self, duration_ms: int, step: int = 100):
        elapsed = 0
        while elapsed < duration_ms:
            # 가중치 기반 자연 유입
            if random.random() < 0.08:
                ids = list(self.stations.keys())
                weights = [self.stations[sid].weight for sid in ids]
                sid = random.choices(ids, weights=weights, k=1)[0]
                try:
                    self.stations[sid].add_passengers(
                        random.randint(1, 4), self.reachable[sid]
                    )
                except (StationOverloadError, StationClosedError):
                    pass
            for t in self.trains:
                t.update_logic(step, self.stations, self.skip_station_ids)
            elapsed += step

    def _get_adjacent_active(self, station_id: str) -> list:
        result = set()
        for route in self.lines:
            if station_id not in route:
                continue
            idx = route.index(station_id)
            for delta in [-1, 1]:
                ni = idx + delta
                if 0 <= ni < len(route):
                    neighbor = route[ni]
                    if neighbor not in self.skip_station_ids:
                        result.add(neighbor)
        return list(result)

    def _redistribute_passengers(self, station_id: str):
        station = self.stations[station_id]
        adjacents = self._get_adjacent_active(station_id)
        if not adjacents:
            return
        stranded = station.waiting_passengers[:]
        station.waiting_passengers = []
        for p in stranded:
            valid = [s for s in adjacents if s != p.destination_id]
            target_sid = random.choice(valid) if valid else random.choice(adjacents)
            if not self.stations[target_sid].is_skipped:
                self.stations[target_sid].waiting_passengers.append(p)

    def _apply_skip(self, station_id: str):
        self.skip_station_ids.add(station_id)
        self.stations[station_id].is_skipped = True
        self._redistribute_passengers(station_id)

    def _apply_extra_train(self, station_id: str):
        for i, route in enumerate(self.lines):
            if station_id in route:
                idx = route.index(station_id)
                start = max(0, idx - 1)
                extra = MetroTrain(
                    f'T-extra-{i}', self.line_colors[i], route, start, 1
                )
                self.trains.append(extra)
                break


# ---------------------------------------------------------
# 3. 병목 감지 및 시나리오 분석기
# ---------------------------------------------------------

class BottleneckAnalyzer:
    """
    병목 자동 감지 및 시나리오 비교 분석기.
    
    감지: 대기 인원이 임계값 초과 시 자동 경고 (방식 A)
    분석: 3가지 처방을 고속 시뮬로 비교 후 최적안 추천 (방식 B)
    """
    BOTTLENECK_THRESHOLD = 20  # 병목 판단 기준 대기 인원

    def detect(self, stations: dict) -> list:
        """임계값 초과 역 목록 반환"""
        return [s for s in stations.values() if len(s) >= self.BOTTLENECK_THRESHOLD and not s.is_skipped]

    def run_scenario(self, system, target_station_id: str, duration_ms=30000) -> dict:
        """
        3가지 처방 시나리오를 각각 고속 시뮬로 돌려 결과 비교.
        
        시나리오:
          A: 현상 유지 (아무것도 안 함)
          B: 해당 역 무정차 → 인접 역으로 승객 분산
          C: 해당 역 열차 추가 배치
        
        Returns: 각 시나리오별 처리 승객 수 및 최대 혼잡도 비교 dict
        """
        results = {}

        for label, setup_fn in [
            ("A: 현상유지",      lambda s: None),
            ("B: 무정차+분산",   lambda s: s._apply_skip(target_station_id)),
            ("C: 열차 추가",     lambda s: s._apply_extra_train(target_station_id)),
        ]:
            sim = system.clone()
            setup_fn(sim)
            sim.fast_forward(duration_ms)
            total_boarded = sum(s.total_boarded for s in sim.stations.values())
            max_crowd = max(s.max_waiting for s in sim.stations.values())
            results[label] = {
                "total_boarded": total_boarded,
                "max_crowd": max_crowd,
            }

        # 총 처리 승객 기준으로 최적 시나리오 결정
        best = max(results, key=lambda k: results[k]["total_boarded"])
        return {"results": results, "best": best}


# ---------------------------------------------------------
# 3. 시뮬레이션 환경 (Pygame 통합)
# ---------------------------------------------------------

class SubwaySystem:
    # 화면 크기
    W, H = 1280, 750

    # 병목 감지 쿨다운 (ms): 같은 역 경고 너무 자주 안 뜨게
    BOTTLENECK_COOLDOWN = 8000

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("MetroSim — OOP Subway Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgungothic", 12)
        self.bold_font = pygame.font.SysFont("malgungothic", 14, bold=True)
        self.title_font = pygame.font.SysFont("malgungothic", 16, bold=True)

        self.alerts = []
        self.skip_station_ids = set()         # 무정차 역 ID 집합
        self.bottleneck_cooldowns = {}        # {station_id: last_alert_time}
        self.analyzer = BottleneckAnalyzer()
        self.scenario_result = None           # 마지막 시나리오 결과
        self.scenario_target = None           # 시나리오 분석 대상 역 이름

        # 방식 A 자동 감지 쿨다운 (전체)
        self.last_bottleneck_check = 0

        self.setup_data()

    # ── 데이터 초기화 ──────────────────────────────────────────

    def setup_data(self):
        """
        역 데이터 설정.
        환승역(교대, 고속터미널, 양재)은 weight를 높게 설정해
        승객이 더 많이 몰리도록 함.
        """
        # (id, 이름, x, y, weight)
        # weight 기본값 1.0 / 환승역 2.5~3.0
        s_data = [
            ('s1',  '강남',      100, 300, 1.0),
            ('s2',  '교대',      200, 300, 2.5),   # 환승역 (2호선+3호선)
            ('s3',  '고속터미널', 300, 200, 3.0),   # 환승역 (3호선+7호선+9호선)
            ('s4',  '반포',      400, 200, 1.0),
            ('s5',  '논현',      500, 200, 1.0),
            ('s6',  '신사',      600, 200, 1.0),
            ('s7',  '남부터미널', 300, 300, 1.2),
            ('s8',  '양재',      400, 300, 2.5),   # 환승역 (3호선+신분당선)
            ('s9',  '매봉',      500, 300, 1.0),
            ('s10', '도곡',      600, 300, 1.0),
            ('s11', '대치',      700, 300, 1.0),
            ('s12', '압구정',    300, 100, 1.5),
            ('s13', '잠원',      400, 100, 1.0),
            ('s14', '학여울',    400, 400, 1.0),
            ('s15', '대청',      400, 500, 1.0),
        ]
        self.stations = {
            sid: Station(sid, name, x, y, weight)
            for sid, name, x, y, weight in s_data
        }

        # 노선 (3개)
        self.lines = [
            ['s1', 's2', 's3', 's4', 's5', 's6'],   # 청색
            ['s2', 's7', 's8', 's9', 's10', 's11'],  # 녹색
            ['s12', 's13', 's4', 's8', 's14', 's15'] # 주황
        ]
        self.line_colors = [
            (0, 82, 164),
            (0, 157, 62),
            (239, 124, 28),
        ]
        self.line_names = ["청색선", "녹색선", "주황선"]

        # 역별 도달 가능 역 계산 (같은 노선 내)
        self.reachable = {}
        for sid in self.stations:
            reach = set()
            for route in self.lines:
                if sid in route:
                    reach.update(route)
            self.reachable[sid] = list(reach)

        # 환승역 ID 집합 (2개 이상 노선 교차)
        self.transfer_ids = set()
        for sid in self.stations:
            count = sum(1 for route in self.lines if sid in route)
            if count >= 2:
                self.transfer_ids.add(sid)

        self.trains = [
            MetroTrain('T-청색', self.line_colors[0], self.lines[0], 0,  1),
            MetroTrain('T-녹색', self.line_colors[1], self.lines[1], 0,  1),
            MetroTrain('T-주황', self.line_colors[2], self.lines[2], 0,  1),
        ]

        # 초기 승객 배치
        for s in self.stations.values():
            count = int(random.randint(0, 10) * s.weight)
            try:
                s.add_passengers(count, self.reachable[s.id])
            except (StationOverloadError, StationClosedError):
                pass

    # ── 무정차 토글 ────────────────────────────────────────────

    def toggle_skip(self, station_id: str):
        """
        역 무정차 토글.
        폐쇄 시: 대기 승객을 인접 활성 역으로 분산.
        재개방 시: 정상화.
        """
        station = self.stations[station_id]

        if station_id not in self.skip_station_ids:
            # 폐쇄
            self.skip_station_ids.add(station_id)
            station.is_skipped = True
            self._redistribute_passengers(station_id)
            self.add_alert(f"🚧 {station.name} 무정차 설정")
        else:
            # 재개방
            self.skip_station_ids.discard(station_id)
            station.is_skipped = False
            self.add_alert(f"✅ {station.name} 무정차 해제")

    def _redistribute_passengers(self, station_id: str):
        """무정차 역 대기 승객을 인접 활성 역으로 랜덤 분산."""
        station = self.stations[station_id]
        adjacents = self._get_adjacent_active(station_id)

        if not adjacents:
            # 인접 활성 역 없으면 가장 가까운 역으로
            adjacents = [self._get_nearest_active(station_id)]

        if not adjacents or adjacents[0] is None:
            return

        stranded = station.waiting_passengers[:]
        station.waiting_passengers = []

        for p in stranded:
            valid = [sid for sid in adjacents if sid != p.destination_id]
            target_sid = random.choice(valid) if valid else random.choice(adjacents)
            target = self.stations[target_sid]
            if not target.is_skipped:
                target.waiting_passengers.append(p)

        self.add_alert(f"  └ {len(stranded)}명 → 인근 역 분산")

    def _get_adjacent_active(self, station_id: str) -> list:
        """노선 상 인접한 활성(무정차 아닌) 역 ID 목록 반환."""
        result = set()
        for route in self.lines:
            if station_id not in route:
                continue
            idx = route.index(station_id)
            for delta in [-1, 1]:
                ni = idx + delta
                if 0 <= ni < len(route):
                    neighbor = route[ni]
                    if neighbor not in self.skip_station_ids:
                        result.add(neighbor)
        return list(result)

    def _get_nearest_active(self, station_id: str) -> str | None:
        """직선거리 기준 가장 가까운 활성 역 ID 반환."""
        s = self.stations[station_id]
        best, best_dist = None, float('inf')
        for sid, st in self.stations.items():
            if sid == station_id or sid in self.skip_station_ids:
                continue
            d = (st.x - s.x) ** 2 + (st.y - s.y) ** 2
            if d < best_dist:
                best_dist = d
                best = sid
        return best

    # ── 승객 유입 (가중치 반영) ────────────────────────────────

    def _spawn_passengers(self):
        """
        매 프레임 승객 자연 유입.
        weight가 높은 역일수록 선택될 확률이 높음.
        """
        if random.random() > 0.08:
            return

        # 가중치 기반 역 선택
        ids = list(self.stations.keys())
        weights = [self.stations[sid].weight for sid in ids]
        sid = random.choices(ids, weights=weights, k=1)[0]

        try:
            count = random.randint(1, 4)
            self.stations[sid].add_passengers(count, self.reachable[sid])
        except StationClosedError:
            # 무정차 역이면 인접 역으로 우회
            for adj in self._get_adjacent_active(sid):
                try:
                    self.stations[adj].add_passengers(1, self.reachable[adj])
                    break
                except (StationOverloadError, StationClosedError):
                    pass
        except StationOverloadError as e:
            self.add_alert(str(e))

    # ── 병목 자동 감지 (방식 A) ────────────────────────────────

    def _check_bottleneck(self):
        """
        병목 자동 감지: 임계값 초과 역 발견 시 경고 추가.
        쿨다운으로 같은 역 경고 반복 방지.
        """
        now = pygame.time.get_ticks()
        bottlenecks = self.analyzer.detect(self.stations)

        for s in bottlenecks:
            last = self.bottleneck_cooldowns.get(s.id, 0)
            if now - last < self.BOTTLENECK_COOLDOWN:
                continue
            self.bottleneck_cooldowns[s.id] = now
            self.add_alert(f"⚠ 병목 감지: {s.name} ({len(s)}명)")
            self.add_alert(f"  └ [분석] 버튼으로 처방 확인")

    # ── 시나리오 분석 (방식 B) ─────────────────────────────────

    def run_analysis(self, target_station_id: str):
        """
        병목 역 기준으로 3가지 처방 시나리오 고속 시뮬 후 결과 저장.
        결과는 draw_scenario_result()에서 화면에 표시됨.
        """
        self.scenario_result = self.analyzer.run_scenario(self, target_station_id)
        self.scenario_target = self.stations[target_station_id].name
        self.add_alert(f"📊 {self.scenario_target} 시나리오 분석 완료")

    def clone(self):
        """
        고속 시뮬용 복사본 생성.
        pygame.Surface 등 pygame 객체는 제외하고
        시뮬레이션 데이터(역, 열차, 승객)만 복사합니다.
        """
        sim = SimSnapshot()

        # 역 복사
        sim.stations = {}
        for sid, s in self.stations.items():
            ns = Station(s.id, s.name, s.x, s.y, s.weight)
            ns.is_skipped = s.is_skipped
            ns.total_boarded = s.total_boarded
            ns.total_alighted = s.total_alighted
            ns.max_waiting = s.max_waiting
            ns.waiting_passengers = [Passenger(p.destination_id) for p in s.waiting_passengers]
            sim.stations[sid] = ns

        # 노선 / 도달 가능 역
        sim.lines = [route[:] for route in self.lines]
        sim.line_colors = self.line_colors[:]
        sim.reachable = {k: v[:] for k, v in self.reachable.items()}
        sim.skip_station_ids = set(self.skip_station_ids)

        # 열차 복사
        sim.trains = []
        for t in self.trains:
            nt = MetroTrain(t.id, t.color, t.route_ids[:], t.current_idx, t.direction)
            nt.target_idx = t.target_idx
            nt.progress = t.progress
            nt.is_stopped = t.is_stopped
            nt.stop_timer = t.stop_timer
            nt.passengers = [Passenger(p.destination_id) for p in t.passengers]
            sim.trains.append(nt)

        return sim

    def fast_forward(self, duration_ms: int, step: int = 100):
        """고속 시뮬레이션: duration_ms 만큼 step 단위로 업데이트."""
        elapsed = 0
        while elapsed < duration_ms:
            self._spawn_passengers()
            for t in self.trains:
                t.update_logic(step, self.stations, self.skip_station_ids)
            elapsed += step

    def _apply_skip(self, station_id: str):
        """시나리오 B: 해당 역 무정차 + 승객 분산 적용."""
        self.skip_station_ids.add(station_id)
        self.stations[station_id].is_skipped = True
        self._redistribute_passengers(station_id)

    def _apply_extra_train(self, station_id: str):
        """
        시나리오 C: 병목 역이 포함된 노선에 열차 1대 추가.
        해당 역 바로 앞 인덱스에서 출발.
        """
        for i, route in enumerate(self.lines):
            if station_id in route:
                idx = route.index(station_id)
                start = max(0, idx - 1)
                extra = MetroTrain(
                    f'T-extra-{i}',
                    self.line_colors[i],
                    route, start, 1
                )
                self.trains.append(extra)
                break

    # ── 알림 ──────────────────────────────────────────────────

    def add_alert(self, msg: str):
        """경보 리스트 추가. 동일 역 경보는 최신화."""
        now = pygame.time.get_ticks()
        for a in self.alerts:
            if msg[:6] in a['msg']:
                a['msg'] = msg
                a['time'] = now
                return
        self.alerts.insert(0, {'msg': msg, 'time': now})
        if len(self.alerts) > 8:
            self.alerts.pop()

    # ── 그리기 ────────────────────────────────────────────────

    def _draw_map(self):
        """노선 및 역 그리기."""
        # 노선
        for i, route in enumerate(self.lines):
            pts = [(self.stations[s].x, self.stations[s].y) for s in route]
            pygame.draw.lines(self.screen, self.line_colors[i], False, pts, 5)

        # 역
        for s in self.stations.values():
            cx, cy = s.x, s.y
            radius = 10 + min(len(s) // 3, 14)

            # 혼잡도 색상
            if s.is_skipped:
                fill_color = (80, 80, 80)
            elif len(s) > 30:
                fill_color = (220, 50, 50)
            elif len(s) > 15:
                fill_color = (230, 160, 30)
            else:
                fill_color = (255, 255, 255)

            # 환승역은 테두리 두껍게
            border_w = 4 if s.id in self.transfer_ids else 2
            pygame.draw.circle(self.screen, fill_color, (cx, cy), radius)
            pygame.draw.circle(self.screen, (30, 30, 30), (cx, cy), radius, border_w)

            # 역 이름 + 대기 인원
            label = f"{s.name}({len(s)})"
            if s.is_skipped:
                label += " 🚧"
            self.screen.blit(
                self.font.render(label, True, (20, 20, 20)),
                (cx - 22, cy + radius + 4)
            )

    def _draw_trains(self):
        """열차 그리기."""
        for t in self.trains:
            curr = self.stations[t.route_ids[t.current_idx]]
            tgt  = self.stations[t.route_ids[t.target_idx]]
            tx = curr.x + (tgt.x - curr.x) * t.progress
            ty = curr.y + (tgt.y - curr.y) * t.progress

            pygame.draw.rect(self.screen, t.color, (tx - 12, ty - 10, 24, 20), border_radius=4)
            self.screen.blit(
                self.font.render(str(len(t.passengers)), True, (255, 255, 255)),
                (tx - 6, ty - 8)
            )

    def _draw_ui(self):
        """우측 패널: 통계, 경보, 시나리오 결과, 조작 안내."""
        now = pygame.time.get_ticks()
        px = 820  # 패널 x 시작

        # ── 통계 패널 ──
        pygame.draw.rect(self.screen, (255, 255, 255), (px, 20, 340, 110), border_radius=8)
        pygame.draw.rect(self.screen, (180, 180, 180), (px, 20, 340, 110), 2, border_radius=8)

        total_p = sum(len(s) for s in self.stations.values())
        max_s   = max(self.stations.values(), key=lambda s: len(s))
        on_train = sum(len(t.passengers) for t in self.trains)

        self.screen.blit(self.title_font.render("📊 System Live Stats", True, (30, 30, 30)), (px + 10, 30))
        self.screen.blit(self.font.render(f"역 대기 합계 : {total_p}명", True, (50, 50, 50)),  (px + 10, 58))
        self.screen.blit(self.font.render(f"열차 탑승 합계: {on_train}명", True, (50, 50, 50)), (px + 10, 76))
        self.screen.blit(self.font.render(f"최대 혼잡역  : {max_s.name} ({len(max_s)}명)", True, (200, 0, 0)), (px + 10, 94))
        self.screen.blit(self.font.render(f"무정차 역 수  : {len(self.skip_station_ids)}개", True, (100, 100, 100)), (px + 10, 112))

        # ── 경보 패널 ──
        pygame.draw.rect(self.screen, (255, 240, 240), (px, 145, 340, 180), border_radius=8)
        pygame.draw.rect(self.screen, (200, 80, 80), (px, 145, 340, 180), 2, border_radius=8)
        self.screen.blit(self.bold_font.render("⚠ Alerts", True, (160, 0, 0)), (px + 10, 153))

        self.alerts = [a for a in self.alerts if now - a['time'] < 7000]
        for i, a in enumerate(self.alerts[:7]):
            alpha = max(60, 255 - int(200 * ((now - a['time']) / 7000)))
            surf = self.font.render(f"• {a['msg']}", True, (180, 0, 0))
            surf.set_alpha(alpha)
            self.screen.blit(surf, (px + 10, 175 + i * 20))

        # ── 시나리오 결과 패널 ──
        if self.scenario_result:
            self._draw_scenario_result(px, 345)

        # ── 조작 안내 ──
        guide_y = 660
        pygame.draw.rect(self.screen, (240, 245, 255), (px, guide_y, 340, 75), border_radius=8)
        pygame.draw.rect(self.screen, (180, 180, 220), (px, guide_y, 340, 75), 1, border_radius=8)
        self.screen.blit(self.bold_font.render("🖱 조작 안내", True, (50, 50, 100)), (px + 10, guide_y + 8))
        self.screen.blit(self.font.render("좌클릭: 역 무정차 토글", True, (60, 60, 60)),  (px + 10, guide_y + 28))
        self.screen.blit(self.font.render("우클릭: 해당 역 시나리오 분석 실행", True, (60, 60, 60)), (px + 10, guide_y + 46))

    def _draw_scenario_result(self, px: int, py: int):
        """시나리오 비교 결과 패널 그리기."""
        results = self.scenario_result["results"]
        best    = self.scenario_result["best"]

        pygame.draw.rect(self.screen, (240, 255, 240), (px, py, 340, 300), border_radius=8)
        pygame.draw.rect(self.screen, (80, 160, 80), (px, py, 340, 300), 2, border_radius=8)
        self.screen.blit(
            self.bold_font.render(f"📋 시나리오 분석: {self.scenario_target}", True, (20, 100, 20)),
            (px + 10, py + 10)
        )
        self.screen.blit(
            self.font.render("(30초 고속 시뮬 기준)", True, (100, 100, 100)),
            (px + 10, py + 30)
        )

        row_y = py + 55
        headers = ["시나리오", "처리승객", "최대혼잡"]
        col_x = [px + 8, px + 170, px + 270]
        for j, h in enumerate(headers):
            self.screen.blit(self.bold_font.render(h, True, (40, 40, 40)), (col_x[j], row_y))

        row_y += 24
        pygame.draw.line(self.screen, (180, 200, 180), (px + 5, row_y), (px + 335, row_y), 1)
        row_y += 6

        for label, data in results.items():
            is_best = (label == best)
            color = (0, 120, 0) if is_best else (60, 60, 60)
            bg_color = (200, 255, 200) if is_best else None

            if bg_color:
                pygame.draw.rect(self.screen, bg_color, (px + 4, row_y - 2, 332, 22), border_radius=4)

            short = label.split(":")[1].strip() if ":" in label else label
            best_mark = " ★" if is_best else ""
            self.screen.blit(self.font.render(short + best_mark, True, color), (col_x[0], row_y))
            self.screen.blit(self.font.render(str(data["total_boarded"]) + "명", True, color), (col_x[1], row_y))
            self.screen.blit(self.font.render(str(data["max_crowd"]) + "명", True, color), (col_x[2], row_y))
            row_y += 26

        # 추천 멘트
        row_y += 10
        rec = best.split(":")[1].strip() if ":" in best else best
        self.screen.blit(
            self.bold_font.render(f"✅ 추천: {rec}", True, (0, 100, 0)),
            (px + 10, row_y)
        )

        # 추천 이유 한 줄
        rec_desc = {
            "현상유지":   "현재 운영이 가장 효율적입니다.",
            "무정차+분산": "승객 분산으로 혼잡이 완화됩니다.",
            "열차 추가":  "배차 증가로 처리량이 늘어납니다.",
        }
        desc = next((v for k, v in rec_desc.items() if k in rec), "")
        self.screen.blit(self.font.render(desc, True, (40, 100, 40)), (px + 10, row_y + 22))

    # ── 메인 루프 ──────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.get_time()
            self.screen.fill((245, 246, 250))

            # 이벤트 처리
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    clicked = self._get_station_at(mx, my)

                    if clicked:
                        if event.button == 1:   # 좌클릭: 무정차 토글
                            self.toggle_skip(clicked)
                        elif event.button == 3: # 우클릭: 시나리오 분석
                            self.run_analysis(clicked)

            # 승객 유입 (가중치 반영)
            self._spawn_passengers()

            # 병목 자동 감지 (방식 A)
            self._check_bottleneck()

            # 열차 업데이트
            for t in self.trains:
                t.update_logic(dt, self.stations, self.skip_station_ids)

            # 그리기
            self._draw_map()
            self._draw_trains()
            self._draw_ui()

            pygame.display.flip()
            self.clock.tick(60)

    def _get_station_at(self, mx: int, my: int) -> str | None:
        """마우스 좌표에서 가장 가까운 역 ID 반환 (클릭 반경 20px)."""
        for sid, s in self.stations.items():
            if (mx - s.x) ** 2 + (my - s.y) ** 2 <= 20 ** 2:
                return sid
        return None


# ---------------------------------------------------------
if __name__ == "__main__":
    SubwaySystem().run()
