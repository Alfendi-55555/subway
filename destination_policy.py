import random


class RandomDestinationPolicy:
    """Chooses a reachable destination without time-based preference."""

    def choose_destination(
        self,
        origin_id: str,
        reachable_dests: list[str],
        clock=None,
        event=None,
    ) -> str | None:
        candidates = [station_id for station_id in reachable_dests if station_id != origin_id]
        if not candidates:
            return None
        return random.choice(candidates)


class RushHourDestinationPolicy(RandomDestinationPolicy):
    """Biases destination choices toward business stations during rush hour."""

    def choose_destination(
        self,
        origin_id: str,
        reachable_dests: list[str],
        clock=None,
        event=None,
    ) -> str | None:
        candidates = [station_id for station_id in reachable_dests if station_id != origin_id]
        if not candidates:
            return None
        if clock is None or event is None or not event.is_active(clock):
            return random.choice(candidates)

        weights = [
            event.destination_multiplier(station_id, clock)
            for station_id in candidates
        ]
        return random.choices(candidates, weights=weights, k=1)[0]
