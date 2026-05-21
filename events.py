class RushHourEvent:
    """일반 상황에 비해 승객량이 증가하고, 특정 역으로의 수요가 몰립니다."""

    NAME = "출근 러시아워"
    START_MINUTE = 7 * 60 + 30
    END_MINUTE = 9 * 60 + 30

    ORIGIN_MULTIPLIERS = {
        "s4": 1.6,   # 반포
        "s5": 1.7,   # 논현
        "s6": 1.8,   # 신사
        "s7": 1.6,   # 남부터미널
        "s9": 1.8,   # 매봉
        "s10": 1.8,  # 도곡
        "s11": 1.7,  # 대치
        "s13": 1.5,  # 잠원
        "s14": 1.7,  # 학여울
        "s15": 1.8,  # 대청
    }
    DESTINATION_MULTIPLIERS = {
        "s1": 4.0,  # 강남
        "s2": 3.0,  # 교대
        "s3": 3.5,  # 고속터미널
        "s8": 3.0,  # 양재
    }
    GLOBAL_MULTIPLIER = 1.25

    def is_active(self, clock) -> bool:
        return clock.is_between(self.START_MINUTE, self.END_MINUTE)

    def origin_multiplier(self, station_id: str, clock) -> float:
        if not self.is_active(clock):
            return 1.0
        return self.ORIGIN_MULTIPLIERS.get(station_id, 1.0)

    def destination_multiplier(self, station_id: str, clock) -> float:
        if not self.is_active(clock):
            return 1.0
        return self.DESTINATION_MULTIPLIERS.get(station_id, 1.0)

    def global_multiplier(self, clock) -> float:
        return self.GLOBAL_MULTIPLIER if self.is_active(clock) else 1.0

    def status_text(self, clock) -> str:
        return self.NAME if self.is_active(clock) else "평상시"

    def destination_names(self, stations: dict) -> str:
        names = [
            stations[station_id].name
            for station_id in self.DESTINATION_MULTIPLIERS
            if station_id in stations
        ]
        return "/".join(names)
