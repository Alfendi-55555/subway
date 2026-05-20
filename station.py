import random

from .exceptions import StationClosedError, StationOverloadError
from .passenger import Passenger


class Station:
    # 역 상태를 담당하는 클래스. 대기 승객/ 승하차 통계/ 무정차 상태 관리 등

    OVERLOAD_THRESHOLD = 65

    def __init__(self, id: str, name: str, x: int, y: int, weight: float = 1.0):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.weight = weight
        self.waiting_passengers: list[Passenger] = []
        self.total_boarded = 0
        self.total_alighted = 0
        self.max_waiting = 0
        self.is_skipped = False
        self.show_indicator = False
        self.last_boarded = 0
        self.last_alighted = 0
        self._indicator_timer = 0

    def __len__(self) -> int:
        return len(self.waiting_passengers)

    def __str__(self) -> str:
        status = " [무정차]" if self.is_skipped else ""
        return f"{self.name}역: {len(self)}명 대기{status}"

    def update(self, dt: float) -> None:
        if self._indicator_timer <= 0:
            self.show_indicator = False
            return

        self._indicator_timer -= dt
        if self._indicator_timer <= 0:
            self.show_indicator = False

    def add_passengers(self, count: int, reachable_dests: list[str]) -> None:
        if self.is_skipped:
            raise StationClosedError(self.name)

        for _ in range(count):
            destination_id = random.choice(reachable_dests)
            self.add_passenger_to(destination_id)

    def add_passenger_to(self, destination_id: str) -> None:
        self.add_passenger(Passenger(destination_id))

    def add_passenger(self, passenger: Passenger) -> None:
        if self.is_skipped:
            raise StationClosedError(self.name)

        if passenger.destination_id != self.id:
            self.waiting_passengers.append(passenger)

        self.max_waiting = max(self.max_waiting, len(self))

        if len(self) > self.OVERLOAD_THRESHOLD:
            raise StationOverloadError(self.name, len(self))

    def record_boarding(self, boarded_count: int) -> None:
        self.total_boarded += boarded_count
        self.last_boarded = boarded_count
        self._refresh_indicator()

    def record_alighting(self, alighted_count: int) -> None:
        self.total_alighted += alighted_count
        self.last_alighted = alighted_count
        self._refresh_indicator()

    def _refresh_indicator(self) -> None:
        if self.last_boarded or self.last_alighted:
            self.show_indicator = True
            self._indicator_timer = 2000
