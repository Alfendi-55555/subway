try:
    from .system import SubwaySystem
except ImportError:
    from pathlib import Path
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from subway_sim.system import SubwaySystem


if __name__ == "__main__":
    SubwaySystem().run()
