from .simulation import Simulation


class SimSnapshot(Simulation):
    """Backward-compatible name for older imports."""

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            super().__init__(*args, **kwargs)
