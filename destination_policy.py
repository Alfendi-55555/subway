from abc import ABC, abstractmethod
import random


class DestinationPolicy(ABC):
    @abstractmethod
    def choose_destination(
        self,
        origin_id: str,
        reachable_dests: list[str],
        clock=None,
        event=None,
    ) -> str | None: ...


class RandomDestinationPolicy(DestinationPolicy):
    """평소에는 승객의 목적지가 랜덤으로 지정"""

    def choose_destination(
        self,
        origin_id: str,
        reachable_dests: list[str],
        clock=None,
        event=None,
    ) -> str | None:
        candidates = [s for s in reachable_dests if s != origin_id]
        if not candidates:
            return None
        return random.choice(candidates)


class RushHourDestinationPolicy(DestinationPolicy):
    """러시아워 시 가중치를 반영해 특정 역으로의 목적지 선호가 증가하도록 지정"""

    def choose_destination(
        self,
        origin_id: str,
        reachable_dests: list[str],
        clock=None,
        event=None,
    ) -> str | None:
        candidates = [s for s in reachable_dests if s != origin_id]
        if not candidates:
            return None
        if clock is None or event is None or not event.is_active(clock):
            return random.choice(candidates)

        weights = [event.destination_multiplier(s, clock) for s in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]
