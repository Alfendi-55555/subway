#t사용자 예외 처리

class StationOverloadError(Exception):
    #역에 사람이 너무 많은 경우 예외처리

    def __init__(self, name: str, count: int):
        super().__init__(f"{name}역 병목!: {count}명 대기")


class StationClosedError(Exception):
    #무정차 역에 승객 추가시 예외처리

    def __init__(self, name: str):
        super().__init__(f"{name}역은 현재 무정차 상태입니다.")

