class Passenger:
    """Passenger data object with one destination station id."""

    def __init__(self, destination_id: str):
        self.destination_id = destination_id

    def __str__(self) -> str:
        return f"Passenger(to={self.destination_id})"

