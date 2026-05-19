import random
import sys

import pygame

from .analyzer import BottleneckAnalyzer
from .data import LINE_COLORS, LINE_NAMES, LINES, STATION_DATA
from .exceptions import StationClosedError, StationOverloadError
from .passenger import Passenger
from .snapshot import SimSnapshot
from .spawner import PassengerSpawner
from .station import Station
from .train import MetroTrain


class SubwaySystem:
    #전체 실행 오케스트레이션 - pygame을 통한 시각화, 이벤트, 열차/역 업데이트

    W, H = 1280, 750
    PANEL_X = 820
    BOTTLENECK_COOLDOWN = 8000

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("MetroSim - OOP Subway Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgungothic", 13)
        self.bold_font = pygame.font.SysFont("malgungothic", 15, bold=True)
        self.title_font = pygame.font.SysFont("malgungothic", 18, bold=True)

        self.alerts = []
        self.skip_station_ids: set[str] = set()
        self.bottleneck_cooldowns = {}
        self.last_bottleneck_check = 0
        self.scenario_result = None
        self.scenario_target = None

        self._spawner = PassengerSpawner()
        self._analyzer = BottleneckAnalyzer()
        self.setup_data()

    def setup_data(self) -> None:
        self.stations = {
            station_id: Station(station_id, name, x, y, weight)
            for station_id, name, x, y, weight in STATION_DATA
        }
        self.lines = [route[:] for route in LINES]
        self.line_colors = LINE_COLORS[:]
        self.line_names = LINE_NAMES[:]
        self.reachable = self._build_reachable()
        self.transfer_ids = self._build_transfer_ids()
        self.trains = [
            MetroTrain("T-Blue", self.line_colors[0], self.lines[0], 0, 1),
            MetroTrain("T-Green", self.line_colors[1], self.lines[1], 0, 1),
            MetroTrain("T-Orange", self.line_colors[2], self.lines[2], 0, 1),
        ]

        for station in self.stations.values():
            count = int(random.randint(0, 10) * station.weight)
            try:
                station.add_passengers(count, self.reachable[station.id])
            except (StationOverloadError, StationClosedError):
                pass

    def _build_reachable(self) -> dict[str, list[str]]:
        reachable = {}
        for station_id in self.stations:
            destinations = set()
            for route in self.lines:
                if station_id in route:
                    destinations.update(route)
            reachable[station_id] = list(destinations)
        return reachable

    def _build_transfer_ids(self) -> set[str]:
        return {
            station_id
            for station_id in self.stations
            if sum(1 for route in self.lines if station_id in route) >= 2
        }

    def clone(self) -> SimSnapshot:
        sim = SimSnapshot()
        sim.stations = {}
        for station_id, station in self.stations.items():
            copied_station = Station(
                station.id,
                station.name,
                station.x,
                station.y,
                station.weight,
            )
            copied_station.is_skipped = station.is_skipped
            copied_station.total_boarded = station.total_boarded
            copied_station.total_alighted = station.total_alighted
            copied_station.max_waiting = station.max_waiting
            copied_station.waiting_passengers = [
                Passenger(passenger.destination_id)
                for passenger in station.waiting_passengers
            ]
            sim.stations[station_id] = copied_station

        sim.lines = [route[:] for route in self.lines]
        sim.line_colors = self.line_colors[:]
        sim.reachable = {
            station_id: destinations[:]
            for station_id, destinations in self.reachable.items()
        }
        sim.skip_station_ids = set(self.skip_station_ids)
        sim.spawner = PassengerSpawner()
        sim.trains = []

        for train in self.trains:
            copied_train = MetroTrain(
                train.id,
                train.color,
                train.route_ids[:],
                train.current_idx,
                train.direction,
            )
            copied_train.target_idx = train.target_idx
            copied_train.progress = train.progress
            copied_train.is_stopped = train.is_stopped
            copied_train.stop_timer = train.stop_timer
            copied_train.passengers = [
                Passenger(passenger.destination_id)
                for passenger in train.passengers
            ]
            sim.trains.append(copied_train)

        return sim

    def toggle_skip(self, station_id: str) -> None:
        station = self.stations[station_id]
        if station_id not in self.skip_station_ids:
            self.skip_station_ids.add(station_id)
            station.is_skipped = True
            self._redistribute_passengers(station_id)
            self.add_alert(f"{station.name} 무정차 설정")
            return

        self.skip_station_ids.discard(station_id)
        station.is_skipped = False
        self.add_alert(f"{station.name} 무정차 해제")

    def _redistribute_passengers(self, station_id: str) -> None:
        station = self.stations[station_id]
        adjacent_ids = self._get_adjacent_active(station_id)
        if not adjacent_ids:
            nearest_id = self._get_nearest_active(station_id)
            adjacent_ids = [nearest_id] if nearest_id else []
        if not adjacent_ids:
            return

        stranded = station.waiting_passengers[:]
        station.waiting_passengers = []
        for passenger in stranded:
            valid_ids = [
                adjacent_id
                for adjacent_id in adjacent_ids
                if adjacent_id != passenger.destination_id
            ]
            target_id = random.choice(valid_ids or adjacent_ids)
            if not self.stations[target_id].is_skipped:
                self.stations[target_id].waiting_passengers.append(passenger)

        self.add_alert(f"{len(stranded)}명 인접 역으로 분산")

    def _get_adjacent_active(self, station_id: str) -> list[str]:
        result = set()
        for route in self.lines:
            if station_id not in route:
                continue
            idx = route.index(station_id)
            for delta in (-1, 1):
                neighbor_idx = idx + delta
                if 0 <= neighbor_idx < len(route):
                    neighbor_id = route[neighbor_idx]
                    if neighbor_id not in self.skip_station_ids:
                        result.add(neighbor_id)
        return list(result)

    def _get_nearest_active(self, station_id: str) -> str | None:
        station = self.stations[station_id]
        best_id = None
        best_distance = float("inf")
        for candidate_id, candidate in self.stations.items():
            if candidate_id == station_id or candidate_id in self.skip_station_ids:
                continue
            distance = (candidate.x - station.x) ** 2 + (candidate.y - station.y) ** 2
            if distance < best_distance:
                best_id = candidate_id
                best_distance = distance
        return best_id

    def _spawn_passengers(self, dt: float) -> None:
        events = self._spawner.tick(self.stations, self.reachable, dt)
        for kind, payload in events:
            if kind == "alert":
                self.add_alert(payload)
                continue
            if kind != "redirect":
                continue

            for adjacent_id in self._get_adjacent_active(payload):
                try:
                    self.stations[adjacent_id].add_passengers(
                        1,
                        self.reachable[adjacent_id],
                    )
                    break
                except (StationOverloadError, StationClosedError):
                    pass

    def _check_bottleneck(self) -> None:
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
        self.scenario_result = self._analyzer.run_scenario(self, target_station_id)
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
        if len(self.alerts) > 8:
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

            for station in self.stations.values():
                station.update(dt)
            for train in self.trains:
                train.update_logic(dt, self.stations, self.skip_station_ids)

            self._draw_map()
            self._draw_trains()
            self._draw_ui()

            pygame.display.flip()
            self.clock.tick(60)

    def _get_station_at(self, mx: int, my: int) -> str | None:
        for station_id, station in self.stations.items():
            if (mx - station.x) ** 2 + (my - station.y) ** 2 <= 20 ** 2:
                return station_id
        return None

    def _draw_map(self) -> None:
        for line_index, route in enumerate(self.lines):
            points = [(self.stations[station_id].x, self.stations[station_id].y) for station_id in route]
            pygame.draw.lines(self.screen, self.line_colors[line_index], False, points, 5)

        for station in self.stations.values():
            radius = 10 + min(len(station) // 3, 14)
            if station.is_skipped:
                fill = (170, 170, 170)
            elif len(station) >= BottleneckAnalyzer.BOTTLENECK_THRESHOLD:
                fill = (255, 90, 90)
            elif station.id in self.transfer_ids:
                fill = (255, 245, 170)
            else:
                fill = (255, 255, 255)

            pygame.draw.circle(self.screen, fill, (station.x, station.y), radius)
            pygame.draw.circle(self.screen, (20, 20, 20), (station.x, station.y), radius, 2)

            if station.id in self.transfer_ids:
                pygame.draw.circle(self.screen, (20, 20, 20), (station.x, station.y), radius + 4, 2)

            label = self.font.render(f"{station.name}({len(station)})", True, (20, 20, 20))
            self.screen.blit(label, (station.x - 30, station.y + radius + 6))

            if station.show_indicator:
                text = f"+{station.last_boarded} / -{station.last_alighted}"
                indicator = self.font.render(text, True, (0, 120, 60))
                self.screen.blit(indicator, (station.x - 28, station.y - radius - 28))

    def _draw_trains(self) -> None:
        for train in self.trains:
            current = self.stations[train.route_ids[train.current_idx]]
            target = self.stations[train.route_ids[train.target_idx]]
            x = current.x + (target.x - current.x) * train.progress
            y = current.y + (target.y - current.y) * train.progress
            pygame.draw.rect(self.screen, train.color, (x - 12, y - 12, 24, 24), border_radius=4)
            pygame.draw.rect(self.screen, (20, 20, 20), (x - 12, y - 12, 24, 24), 2, border_radius=4)
            label = self.font.render(str(len(train)), True, (255, 255, 255))
            self.screen.blit(label, (x - 6, y - 8))

    def _draw_ui(self) -> None:
        self._draw_panel((self.PANEL_X, 20, 420, 115), "Stats")
        self._draw_stats()
        self._draw_panel((self.PANEL_X, 150, 420, 185), "Alerts")
        self._draw_alerts()
        self._draw_panel((self.PANEL_X, 350, 420, 285), "Scenario")
        self._draw_scenario_result()
        self._draw_panel((self.PANEL_X, 668, 420, 60), "Controls")
        self._draw_controls()

    def _draw_panel(self, rect: tuple[int, int, int, int], title: str) -> None:
        pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=8)
        pygame.draw.rect(self.screen, (35, 40, 48), rect, 2, border_radius=8)
        self.screen.blit(self.title_font.render(title, True, (20, 20, 20)), (rect[0] + 12, rect[1] + 8))

    def _draw_stats(self) -> None:
        total_waiting = sum(len(station) for station in self.stations.values())
        max_station = max(self.stations.values(), key=lambda station: len(station))
        total_boarded = sum(station.total_boarded for station in self.stations.values())
        rows = [
            f"대기 승객: {total_waiting}명",
            f"최대 혼잡: {max_station.name} {len(max_station)}명",
            f"누적 탑승: {total_boarded}명",
            f"무정차 역: {len(self.skip_station_ids)}개",
        ]
        for index, row in enumerate(rows):
            self.screen.blit(self.font.render(row, True, (45, 45, 45)), (self.PANEL_X + 14, 56 + index * 19))

    def _draw_alerts(self) -> None:
        now = pygame.time.get_ticks()
        self.alerts = [alert for alert in self.alerts if now - alert["time"] < 5000]
        for index, alert in enumerate(self.alerts[:7]):
            age = now - alert["time"]
            alpha = max(80, 255 - int(255 * age / 5000))
            text = self.font.render(alert["msg"], True, (180, 30, 30))
            text.set_alpha(alpha)
            self.screen.blit(text, (self.PANEL_X + 14, 186 + index * 20))

    def _draw_scenario_result(self) -> None:
        if not self.scenario_result:
            rows = [
                "역을 우클릭하면 30초 고속 시뮬레이션으로",
                "A 현상유지 / B 무정차 / C 열차추가를 비교합니다.",
            ]
            for index, row in enumerate(rows):
                self.screen.blit(self.font.render(row, True, (70, 70, 70)), (self.PANEL_X + 14, 388 + index * 22))
            return

        y = 388
        self.screen.blit(
            self.bold_font.render(f"대상: {self.scenario_target}", True, (20, 20, 20)),
            (self.PANEL_X + 14, y),
        )
        y += 30
        for label, values in self.scenario_result["results"].items():
            score = self.scenario_result["scores"][label]
            row = f"{label}  처리 {values['total_boarded']}명 / 혼잡 {values['max_crowd']} / 점수 {score:.2f}"
            self.screen.blit(self.font.render(row, True, (40, 40, 40)), (self.PANEL_X + 14, y))
            y += 28

        best = self.scenario_result["best"]
        self.screen.blit(
            self.bold_font.render(f"추천: {best}", True, (0, 110, 60)),
            (self.PANEL_X + 14, y + 10),
        )

    def _draw_controls(self) -> None:
        rows = [
            "좌클릭: 무정차 토글",
            "우클릭: 병목 처방 시나리오 분석",
        ]
        for index, row in enumerate(rows):
            self.screen.blit(self.font.render(row, True, (55, 55, 55)), (self.PANEL_X + 14, 700 + index * 20))
