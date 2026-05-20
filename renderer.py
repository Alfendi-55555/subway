import pygame

from .analyzer import BottleneckAnalyzer


class SubwayRenderer:
    """Draws the subway simulation without owning simulation rules."""

    def draw(self, system) -> None:
        self._draw_map(system)
        self._draw_trains(system)
        self._draw_ui(system)

    def _draw_map(self, system) -> None:
        for line_index, route in enumerate(system.lines):
            points = [
                (system.stations[station_id].x, system.stations[station_id].y)
                for station_id in route
            ]
            pygame.draw.lines(system.screen, system.line_colors[line_index], False, points, 5)

        for station in system.stations.values():
            radius = 10 + min(len(station) // 3, 14)
            if station.is_skipped:
                fill = (170, 170, 170)
            elif len(station) >= BottleneckAnalyzer.BOTTLENECK_THRESHOLD:
                fill = (255, 90, 90)
            elif station.id in system.transfer_ids:
                fill = (255, 245, 170)
            else:
                fill = (255, 255, 255)

            pygame.draw.circle(system.screen, fill, (station.x, station.y), radius)
            pygame.draw.circle(system.screen, (20, 20, 20), (station.x, station.y), radius, 2)

            if station.id in system.transfer_ids:
                pygame.draw.circle(system.screen, (20, 20, 20), (station.x, station.y), radius + 4, 2)

            label = system.font.render(f"{station.name}({len(station)})", True, (20, 20, 20))
            system.screen.blit(label, (station.x - 30, station.y + radius + 6))

            if station.show_indicator:
                text = f"+{station.last_boarded} / -{station.last_alighted}"
                indicator = system.font.render(text, True, (0, 120, 60))
                system.screen.blit(indicator, (station.x - 28, station.y - radius - 28))

    def _draw_trains(self, system) -> None:
        for train in system.trains:
            current = system.stations[train.route_ids[train.current_idx]]
            target = system.stations[train.route_ids[train.target_idx]]
            x = current.x + (target.x - current.x) * train.progress
            y = current.y + (target.y - current.y) * train.progress
            pygame.draw.rect(system.screen, train.color, (x - 12, y - 12, 24, 24), border_radius=4)
            pygame.draw.rect(system.screen, (20, 20, 20), (x - 12, y - 12, 24, 24), 2, border_radius=4)
            label = system.font.render(str(len(train)), True, (255, 255, 255))
            system.screen.blit(label, (x - 6, y - 8))

    def _draw_ui(self, system) -> None:
        self._draw_panel(system, (system.PANEL_X, 15, 420, 160), "Stats")
        self._draw_stats(system)
        self._draw_panel(system, (system.PANEL_X, 185, 420, 165), "Alerts")
        self._draw_alerts(system)
        self._draw_panel(system, (system.PANEL_X, 360, 420, 275), "Scenario")
        self._draw_scenario_result(system)
        self._draw_panel(system, (system.PANEL_X, 645, 420, 80), "Controls")
        self._draw_controls(system)

    def _draw_panel(self, system, rect: tuple[int, int, int, int], title: str) -> None:
        pygame.draw.rect(system.screen, (255, 255, 255), rect, border_radius=8)
        pygame.draw.rect(system.screen, (35, 40, 48), rect, 2, border_radius=8)
        system.screen.blit(system.title_font.render(title, True, (20, 20, 20)), (rect[0] + 12, rect[1] + 8))

    def _draw_stats(self, system) -> None:
        total_waiting = sum(len(station) for station in system.stations.values())
        max_station = max(system.stations.values(), key=lambda station: len(station))
        total_boarded = sum(station.total_boarded for station in system.stations.values())
        rows = [
            f"대기 승객: {total_waiting}명",
            f"최대 혼잡: {max_station.name} {len(max_station)}명",
            f"누적 탑승: {total_boarded}명",
            f"무정차 역: {len(system.skip_station_ids)}개",
            f"시뮬 시간: {system.sim.clock}",
            f"이벤트: {system.sim.rush_hour_event.status_text(system.sim.clock)}",
        ]
        for index, row in enumerate(rows):
            system.screen.blit(system.font.render(row, True, (45, 45, 45)), (system.PANEL_X + 14, 50 + index * 19))

    def _draw_alerts(self, system) -> None:
        now = pygame.time.get_ticks()
        system.alerts = [alert for alert in system.alerts if now - alert["time"] < 5000]
        for index, alert in enumerate(system.alerts[:6]):
            age = now - alert["time"]
            alpha = max(80, 255 - int(255 * age / 5000))
            text = system.font.render(alert["msg"], True, (180, 30, 30))
            text.set_alpha(alpha)
            system.screen.blit(text, (system.PANEL_X + 14, 220 + index * 20))

    def _draw_scenario_result(self, system) -> None:
        if not system.scenario_result:
            rows = [
                "역을 우클릭하면 30초 고속 시뮬레이션으로",
                "현상유지 / 무정차 / 열차 추가 시나리오를 비교합니다.",
            ]
            for index, row in enumerate(rows):
                system.screen.blit(system.font.render(row, True, (70, 70, 70)), (system.PANEL_X + 14, 398 + index * 22))
            return

        y = 398
        system.screen.blit(
            system.bold_font.render(f"대상: {system.scenario_target}", True, (20, 20, 20)),
            (system.PANEL_X + 14, y),
        )
        y += 30
        for label, values in system.scenario_result["results"].items():
            score = system.scenario_result["scores"][label]
            boarded = values["total_boarded"]
            overloaded = values["overloaded_stations"]
            progress = values["train_progress"]
            row = f"{label[:4]} 처리 {boarded}명 / 과부하 {overloaded}역 / 흐름 {progress:.1f} / 점수 {score:.2f}"
            system.screen.blit(system.font.render(row, True, (40, 40, 40)), (system.PANEL_X + 14, y))
            y += 28

        best = system.scenario_result["best"]
        system.screen.blit(
            system.bold_font.render(f"추천: {best}", True, (0, 110, 60)),
            (system.PANEL_X + 14, y + 10),
        )

    def _draw_controls(self, system) -> None:
        rows = [
            "좌클릭: 무정차 토글",
            "우클릭: 병목 처방 시나리오 분석",
        ]
        for index, row in enumerate(rows):
            system.screen.blit(system.font.render(row, True, (55, 55, 55)), (system.PANEL_X + 14, 680 + index * 20))
