import random

from .clock import SimulationClock
from .data import LINE_COLORS, LINE_NAMES, LINES, STATION_DATA
from .destination_policy import DestinationPolicy, RushHourDestinationPolicy
from .events import RushHourEvent
from .exceptions import StationClosedError, StationOverloadError
from .passenger import Passenger
from .spawner import PassengerSpawner
from .station import Station
from .train import MetroTrain


class Simulation:
    """시뮬레이션 상태를 구현하는 클래스"""

    MAX_EXTRA_TRAINS = 3 #최대 추가 가능 열차 수(3+3 총 6대)

    def __init__(
        self,
        stations: dict[str, Station],
        lines: list[list[str]],
        line_colors: list[tuple[int, int, int]],
        line_names: list[str],
        trains: list[MetroTrain],
        reachable: dict[str, list[str]] | None = None,
        transfer_ids: set[str] | None = None,
        skip_station_ids: set[str] | None = None,
        spawner: PassengerSpawner | None = None,
        clock: SimulationClock | None = None,
        rush_hour_event: RushHourEvent | None = None,
        destination_policy: RushHourDestinationPolicy | None = None,
    ):
        self.stations = stations
        self.lines = lines
        self.line_colors = line_colors
        self.line_names = line_names
        self.trains = trains
        self.skip_station_ids = skip_station_ids or set()
        self.spawner = spawner or PassengerSpawner()
        self.clock = clock or SimulationClock()
        self.rush_hour_event = rush_hour_event or RushHourEvent()
        self.destination_policy = destination_policy or RushHourDestinationPolicy()
        self.reachable = reachable or self._build_reachable()
        self.transfer_ids = transfer_ids or self._build_transfer_ids()
        self.extra_train_count = 0

    @classmethod
    def from_default_data(cls) -> "Simulation":
        stations = {
            station_id: Station(station_id, name, x, y, weight)
            for station_id, name, x, y, weight in STATION_DATA
        }
        lines = [route[:] for route in LINES]
        line_colors = LINE_COLORS[:]
        line_names = LINE_NAMES[:]
        trains = [
            MetroTrain("T-Blue", line_colors[0], lines[0], 0, 1),
            MetroTrain("T-Green", line_colors[1], lines[1], 0, 1),
            MetroTrain("T-Orange", line_colors[2], lines[2], 0, 1),
        ]
        sim = cls(stations, lines, line_colors, line_names, trains)
        sim.seed_initial_passengers()
        # 시작 시 각 열차가 첫 역에서 한 차례 승하차를 수행하고 즉시 출발하도록 한다.
        # (그러지 않으면 시작 직후 약 2초간 정지 상태로 보이며, 그 동안 승객도 태우지 않는다.)
        for train in trains:
            start_station = stations[train.route_ids[train.current_idx]]
            train.handle_boarding(start_station, sim.skip_station_ids)
            train.is_stopped = False
        return sim

    def seed_initial_passengers(self) -> None:
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

    def clone(self) -> "Simulation":
        copied_stations = {}
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
            copied_stations[station_id] = copied_station

        copied_trains = []
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
            copied_trains.append(copied_train)

        cloned = Simulation(
            copied_stations,
            [route[:] for route in self.lines],
            self.line_colors[:],
            self.line_names[:],
            copied_trains,
            {
                station_id: destinations[:]
                for station_id, destinations in self.reachable.items()
            },
            set(self.transfer_ids),
            set(self.skip_station_ids),
            PassengerSpawner(),
            self.clock.copy(),
            RushHourEvent(),
            self.destination_policy,
        )
        cloned.extra_train_count = self.extra_train_count
        return cloned

    def toggle_skip(self, station_id: str) -> tuple[str, str, int]:
        station = self.stations[station_id]
        if station_id not in self.skip_station_ids:
            self.skip_station_ids.add(station_id)
            station.is_skipped = True
            moved_count = self.redistribute_passengers(station_id)
            return "skipped", station.name, moved_count

        self.skip_station_ids.discard(station_id)
        station.is_skipped = False
        return "active", station.name, 0

    def get_adjacent_active(self, station_id: str) -> list[str]:
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

    def get_nearest_active(self, station_id: str) -> str | None:
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

    def redistribute_passengers(self, station_id: str) -> int:
        station = self.stations[station_id]
        adjacent_ids = self.get_adjacent_active(station_id)
        if not adjacent_ids:
            nearest_id = self.get_nearest_active(station_id)
            adjacent_ids = [nearest_id] if nearest_id else []
        if not adjacent_ids:
            return 0

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
                try:
                    self.stations[target_id].add_passenger(passenger)
                except (StationOverloadError, StationClosedError):
                    pass
        return len(stranded)

    def spawn_passengers(self, dt: float) -> list[tuple[str, str]]:
        self.clock.update(dt)
        events = self.spawner.tick(
            self.stations,
            self.reachable,
            dt,
            self.clock,
            self.rush_hour_event,
            self.destination_policy,
            self.skip_station_ids,
        )
        visible_events = []
        for kind, payload in events:
            if kind == "alert":
                visible_events.append((kind, payload))
                continue
            if kind == "redirect":
                self.redirect_to_adjacent(payload)
        return visible_events

    def redirect_to_adjacent(self, station_id: str) -> bool:
        for adjacent_id in self.get_adjacent_active(station_id):
            try:
                destination_id = self.destination_policy.choose_destination(
                    adjacent_id,
                    self.reachable[adjacent_id],
                    self.clock,
                    self.rush_hour_event,
                    self.skip_station_ids,
                )
                if not destination_id:
                    continue
                self.stations[adjacent_id].add_passenger_to(destination_id)
                return True
            except (StationOverloadError, StationClosedError):
                pass
        return False

    def update(self, dt: float) -> None:
        for station in self.stations.values():
            station.update(dt)
        for train in self.trains:
            train.update_logic(dt, self.stations, self.skip_station_ids)

    def tick(self, dt: float) -> list[tuple[str, str]]:
        events = self.spawn_passengers(dt)
        self.update(dt)
        return events

    def fast_forward(self, duration_ms: int, step: int = 100) -> None:
        elapsed = 0
        while elapsed < duration_ms:
            self.tick(step)
            elapsed += step

    def apply_skip(self, station_id: str) -> None:
        self.skip_station_ids.add(station_id)
        self.stations[station_id].is_skipped = True
        self.redistribute_passengers(station_id)

    def apply_extra_train(self, station_id: str) -> None:
        for line_index, route in enumerate(self.lines):
            if station_id not in route:
                continue
            station_index = route.index(station_id)
            # 새 열차의 "다음 정차"가 항상 타겟 역이 되도록 출발 위치/방향을 잡는다.
            # 노선 첫 역이면 그 다음 역에서 역방향으로, 그 외에는 한 칸 앞에서 정방향으로.
            if station_index == 0:
                start_index = 1
                direction = -1
            else:
                start_index = station_index - 1
                direction = 1
            extra = MetroTrain(
                f"T-extra-{line_index}",
                self.line_colors[line_index],
                route[:],
                start_index,
                direction,
            )
            extra.progress = 0.5
            extra.is_stopped = False
            self.trains.append(extra)
            break

    def add_user_train(self, station_id: str) -> bool:
        """사용자 조작용 열차 추가. 제한 초과 시 False 반환."""
        if self.extra_train_count >= self.MAX_EXTRA_TRAINS:
            return False
        self.apply_extra_train(station_id)
        self.extra_train_count += 1
        return True
