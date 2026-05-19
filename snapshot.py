import random

from .exceptions import StationClosedError, StationOverloadError
from .train import MetroTrain


class SimSnapshot:
    """Lightweight scenario copy with no pygame objects."""

    def fast_forward(self, duration_ms: int, step: int = 100) -> None:
        elapsed = 0
        while elapsed < duration_ms:
            events = self.spawner.tick(self.stations, self.reachable, step)
            self._handle_spawn_events(events)
            for train in self.trains:
                train.update_logic(step, self.stations, self.skip_station_ids)
            for station in self.stations.values():
                station.update(step)
            elapsed += step

    def _handle_spawn_events(self, events: list[tuple[str, str]]) -> None:
        for kind, payload in events:
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

    def _redistribute_passengers(self, station_id: str) -> None:
        station = self.stations[station_id]
        adjacent_ids = self._get_adjacent_active(station_id)
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

    def _apply_skip(self, station_id: str) -> None:
        self.skip_station_ids.add(station_id)
        self.stations[station_id].is_skipped = True
        self._redistribute_passengers(station_id)

    def _apply_extra_train(self, station_id: str) -> None:
        for line_index, route in enumerate(self.lines):
            if station_id not in route:
                continue
            station_index = route.index(station_id)
            start_index = max(0, station_index - 1)
            extra = MetroTrain(
                f"T-extra-{line_index}",
                self.line_colors[line_index],
                route,
                start_index,
                1,
            )
            extra.progress = 0.5
            self.trains.append(extra)
            break

