import sys

import pygame

try:
    from .analyzer import BottleneckAnalyzer
    from .renderer import SubwayRenderer
    from .simulation import Simulation
except ImportError:
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from subway_sim_more.analyzer import BottleneckAnalyzer
    from subway_sim_more.renderer import SubwayRenderer
    from subway_sim_more.simulation import Simulation


class SubwaySystem:
    #전체 실행 오케스트레이션 - pygame을 통한 시각화, 이벤트, 열차/역 업데이트

    W, H = 1280, 750
    PANEL_X = 820
    BOTTLENECK_COOLDOWN = 8000

    #pygame 세팅... 창 이름, 폰트 불러오기 등등
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("MetroSim - OOP Subway Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgungothic", 13)
        self.bold_font = pygame.font.SysFont("malgungothic", 15, bold=True)
        self.title_font = pygame.font.SysFont("malgungothic", 18, bold=True)

        self.alerts = []
        self.bottleneck_cooldowns = {}
        self.last_bottleneck_check = 0
        self.scenario_result = None
        self.scenario_target = None

        self._analyzer = BottleneckAnalyzer()
        self.renderer = SubwayRenderer()
        self.setup_data()

    #데이터 세팅
    def setup_data(self):
        self.sim = Simulation.from_default_data()

    @property
    def stations(self):
        return self.sim.stations

    @property
    def lines(self):
        return self.sim.lines

    @property
    def line_colors(self):
        return self.sim.line_colors

    @property
    def line_names(self):
        return self.sim.line_names

    @property
    def reachable(self):
        return self.sim.reachable

    @property
    def transfer_ids(self):
        return self.sim.transfer_ids

    @property
    def trains(self):
        return self.sim.trains

    @property
    def skip_station_ids(self):
        return self.sim.skip_station_ids

    def _build_reachable(self):
        return self.sim._build_reachable()

    def _build_transfer_ids(self):
        return self.sim._build_transfer_ids()
    
    #시뮬레이션 상황을 복제 => 3개의 시나리오로 시뮬레이션을 돌려봄
    def clone(self) -> Simulation:
        return self.sim.clone()

    def toggle_skip(self, station_id: str):
        status, station_name, moved_count = self.sim.toggle_skip(station_id)
        if status == "skipped":
            self.add_alert(f"{moved_count}명 인접 역으로 분산")
            self.add_alert(f"{station_name} 무정차 설정")
            return
        self.add_alert(f"{station_name} 무정차 해제")

    def _redistribute_passengers(self, station_id: str):
        moved_count = self.sim.redistribute_passengers(station_id)
        self.add_alert(f"{moved_count}명 인접 역으로 분산")

    def _get_adjacent_active(self, station_id: str):
        return self.sim.get_adjacent_active(station_id)

    def _get_nearest_active(self, station_id: str):
        return self.sim.get_nearest_active(station_id)

    def _spawn_passengers(self, dt: float):
        events = self.sim.spawn_passengers(dt)
        for kind, payload in events:
            if kind == "alert":
                self.add_alert(payload)

    def _check_bottleneck(self):
        now = pygame.time.get_ticks()
        if now - self.last_bottleneck_check < 1000:
            return
        self.last_bottleneck_check = now

        for station in self._analyzer.detect(self.stations):
            last = self.bottleneck_cooldowns.get(station.id, 0)
            if now - last < self.BOTTLENECK_COOLDOWN:
                continue
            self.bottleneck_cooldowns[station.id] = now
            self.add_alert(f"병목 감지: {station.name} ({len(station)}명)")
            self.add_alert("우클릭으로 처방 시나리오 분석")

    def run_analysis(self, target_station_id: str) -> None:
        self.scenario_result = self._analyzer.run_scenario(self.sim, target_station_id)
        self.scenario_target = self.stations[target_station_id].name
        self.add_alert(f"{self.scenario_target} 시나리오 분석 완료")

    def add_alert(self, msg: str) -> None:
        now = pygame.time.get_ticks()
        for alert in self.alerts:
            if msg[:6] in alert["msg"]:
                alert["msg"] = msg
                alert["time"] = now
                return
        self.alerts.insert(0, {"msg": msg, "time": now})
        if len(self.alerts) > 6:
            self.alerts.pop()

    def run(self) -> None:
        while True:
            dt = self.clock.get_time()
            self.screen.fill((245, 246, 250))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    clicked = self._get_station_at(*event.pos)
                    if clicked and event.button == 1:
                        self.toggle_skip(clicked)
                    elif clicked and event.button == 3:
                        self.run_analysis(clicked)

            self._spawn_passengers(dt)
            self._check_bottleneck()

            self.sim.update(dt)

            self.renderer.draw(self)

            pygame.display.flip()
            self.clock.tick(60)

    def _get_station_at(self, mx: int, my: int) -> str | None:
        for station_id, station in self.stations.items():
            if (mx - station.x) ** 2 + (my - station.y) ** 2 <= 20 ** 2:
                return station_id
        return None
