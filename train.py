from .passenger import Passenger
from .station import Station

#부모 클래스: 열차의 기본형
#속성: 열차 아이디, 색깔(rgb 튜플), 노선도(문자열 리스트)

class BaseTrain:
    """Parent class for shared train properties."""

    def __init__(self, id: str, color: tuple[int, int, int], route_ids: list[str]):
        self.id = id
        self.color = color
        self.route_ids = route_ids
        self.passengers: list[Passenger] = []


#자식 클래스: 열차의 움직임과 정차 로직
#자체생성 변수: 시작 위치, 경로, 이동 방향(1 or -1)
class MetroTrain(BaseTrain):
    """Train movement and boarding logic."""

    CAPACITY = 40 #최대 승차 인원

    def __init__(self, id: str, color: tuple[int, int, int], route_ids: list[str], start_index: int, direction: int):
        super().__init__(id, color, route_ids)          #부모 클래스에서 아이디, 색깔, 노선도를 물려받음
        self.current_idx = start_index                  #현재 역 위치
        self.direction = direction                      #방향
        self.target_idx = start_index + direction       #다음 정류장 인덱스
        self.progress = 0.0                             #노선 진행률(0~1)
        self.is_stopped = True                          #정차 여부
        self.stop_timer = 0                             #정차 시간

    def __len__(self) -> int:
        return len(self.passengers) #탑승한 승객 수를 반환

    def update_logic(self,dt: float, stations_dict: dict[str, Station],skip_station_ids: set[str]):
        if self.is_stopped:
            self.stop_timer += dt

            # [추가된 로직] 현재 역의 대기 인원에 비례하여 정차 시간 증가
            current_station = stations_dict[self.route_ids[self.current_idx]]
            # 기본 1.5초 + (승객 1명당 50ms 지연). 최대 5초까지만 정차하도록 제한
            required_stop_time = 1500 + min(len(current_station) * 50, 5000)


            if self.stop_timer > required_stop_time:
                self.is_stopped = False
                self.stop_timer = 0
                self.set_next_target()
            return

        self.progress += dt / 2000.0
        if self.progress < 1.0:
            return

        self.progress = 0.0
        self.current_idx = self.target_idx
        current_station_id = self.route_ids[self.current_idx]

        if current_station_id in skip_station_ids:
            # 무정차 역을 통과할 때, 그 역을 목적지로 한 탑승객은 강제 하차시킨다.
            # (현실 비유: "이 역은 무정차로 바뀌었으니 다음 정차역에서 알아서 내리세요")
            self.passengers = [
                passenger
                for passenger in self.passengers
                if passenger.destination_id != current_station_id
            ]
            self.set_next_target()
            return

        self.is_stopped = True
        self.handle_boarding(stations_dict[current_station_id], skip_station_ids)

    def set_next_target(self):
        next_idx = self.current_idx + self.direction
        if next_idx >= len(self.route_ids) or next_idx < 0:
            self.direction *= -1
        self.target_idx = self.current_idx + self.direction

    def handle_boarding(self, station: Station, skip_station_ids: set[str] | None = None):
        skip = skip_station_ids or set()
        initial_count = len(self.passengers)
        self.passengers = [
            passenger
            for passenger in self.passengers
            if passenger.destination_id != station.id
        ]
        station.record_alighting(initial_count - len(self.passengers))

        space = self.CAPACITY - len(self.passengers)
        # 무정차 역을 목적지로 한 승객은 승차시키지 않는다 (열차에 갇히는 것을 방지).
        can_board = [
            passenger
            for passenger in station.waiting_passengers
            if passenger.destination_id in self.route_ids
            and passenger.destination_id not in skip
        ]
        cannot_board = [
            passenger
            for passenger in station.waiting_passengers
            if passenger.destination_id not in self.route_ids
            or passenger.destination_id in skip
        ]

        boarding = can_board[:space]
        station.set_waiting(can_board[space:] + cannot_board)
        self.passengers.extend(boarding)
        station.record_boarding(len(boarding))
