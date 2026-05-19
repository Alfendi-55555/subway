import random

from .exceptions import StationClosedError, StationOverloadError
from .station import Station


class PassengerSpawner:
    """Pygame-free passenger inflow helper used by live and fast simulations."""

    EXPECTED_PER_SECOND = 4.8

    def tick(
        self,
        stations: dict[str, Station],
        reachable: dict[str, list[str]],
        dt: float,
    ) -> list[tuple[str, str]]:
        events: list[tuple[str, str]] = []
        probability = self.EXPECTED_PER_SECOND * max(0, dt) / 1000.0
        spawn_count = int(probability)
        if random.random() < probability - spawn_count:
            spawn_count += 1

        ids = list(stations.keys())
        weights = [stations[station_id].weight for station_id in ids]

        for _ in range(spawn_count):
            station_id = random.choices(ids, weights=weights, k=1)[0]
            try:
                stations[station_id].add_passengers(
                    random.randint(1, 4),
                    reachable[station_id],
                )
            except StationClosedError:
                events.append(("redirect", station_id))
            except StationOverloadError as error:
                events.append(("alert", str(error)))

        return events

