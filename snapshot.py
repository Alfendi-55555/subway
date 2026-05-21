from .simulation import Simulation


class SimSnapshot(Simulation):
    """고속 시뮬레이션을 구현하는 클래스로 사용되었으나
    중복 코드를 개선하는 과정에서 실시간 시뮬레이션과 고속 시뮬레이션의 코드를 Simulation.py로 통합함에 따라,
    혹시 모를 기존 코드와의 호환 문제를 방지하기 위해 임시로 남겨놓았습니다."""

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            super().__init__(*args, **kwargs)
