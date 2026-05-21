#승객 클래스(목적지 아이디를 변수로 가짐)

class Passenger:

    def __init__(self, destination_id: str):
        self.destination_id = destination_id

    def __str__(self):
        return f"Passenger(to={self.destination_id})"

