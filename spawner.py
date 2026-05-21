import random

from .destination_policy import DestinationPolicy, RandomDestinationPolicy
from .exceptions import StationClosedError, StationOverloadError
from .station import Station


class PassengerSpawner:
    """실시간/고속 시뮬레이션에서 승객 생성을 관리하는 클래스"""

    EXPECTED_PER_SECOND = 3.5

    def tick(
        self,
        stations: dict[str, Station],
        reachable: dict[str, list[str]],
        dt: float,
        clock=None,
        event=None,
        destination_policy=None,
    ) -> list[tuple[str, str]]:
        events: list[tuple[str, str]] = []
        event_multiplier = event.global_multiplier(clock) if event and clock else 1.0
        probability = self.EXPECTED_PER_SECOND * event_multiplier * max(0, dt) / 1000.0
        spawn_count = int(probability)
        if random.random() < probability - spawn_count:
            spawn_count += 1

        ids = list(stations.keys())
        weights = [
            stations[station_id].weight
            * (event.origin_multiplier(station_id, clock) if event and clock else 1.0)
            for station_id in ids
        ]
        policy = destination_policy or RandomDestinationPolicy()

        for _ in range(spawn_count):
            station_id = random.choices(ids, weights=weights, k=1)[0]
            try:
                for _ in range(random.randint(1, 4)):
                    destination_id = policy.choose_destination(
                        station_id,
                        reachable[station_id],
                        clock,
                        event,
                    )
                    if destination_id:
                        stations[station_id].add_passenger_to(destination_id)
            except StationClosedError:
                events.append(("redirect", station_id))
            except StationOverloadError as error:
                events.append(("alert", str(error)))

        return events
