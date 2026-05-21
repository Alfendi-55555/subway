class SimulationClock:
    """내부적으로 돌아가는 시뮬레이션 시간(시뮬레이션상 2분이 현실에서는 약 1초)"""

    MINUTES_PER_DAY = 24 * 60

    def __init__(
        self,
        start_hour: int = 7,
        start_minute: int = 0,
        time_scale: float = 120.0,
    ):
        self.current_minutes = (start_hour * 60 + start_minute) % self.MINUTES_PER_DAY
        self.time_scale = time_scale

    def update(self, real_dt_ms: float) -> None:
        sim_minutes = (max(0, real_dt_ms) / 1000.0) * (self.time_scale / 60.0)
        self.current_minutes = (self.current_minutes + sim_minutes) % self.MINUTES_PER_DAY

    def copy(self) -> "SimulationClock":
        copied = SimulationClock(time_scale=self.time_scale)
        copied.current_minutes = self.current_minutes
        return copied

    def is_between(self, start_minute: int, end_minute: int) -> bool:
        current = int(self.current_minutes) % self.MINUTES_PER_DAY
        start = start_minute % self.MINUTES_PER_DAY
        end = end_minute % self.MINUTES_PER_DAY
        if start <= end:
            return start <= current < end
        return current >= start or current < end

    def __str__(self) -> str:
        total = int(self.current_minutes) % self.MINUTES_PER_DAY
        hour = total // 60
        minute = total % 60
        return f"{hour:02d}:{minute:02d}"
