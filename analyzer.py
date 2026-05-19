from __future__ import annotations

from .station import Station


class BottleneckAnalyzer:
    """Detects bottlenecks and compares treatment scenarios."""

    BOTTLENECK_THRESHOLD = 20

    def detect(self, stations: dict[str, Station]) -> list[Station]:
        return [
            station
            for station in stations.values()
            if len(station) >= self.BOTTLENECK_THRESHOLD and not station.is_skipped
        ]

    def run_scenario(
        self,
        system,
        target_station_id: str,
        duration_ms: int = 30000,
    ):
        results = {}
        scenarios = [
            ("A: 현상유지", lambda snapshot: None),
            ("B: 무정차 분산", lambda snapshot: snapshot._apply_skip(target_station_id)),
            ("C: 열차 추가", lambda snapshot: snapshot._apply_extra_train(target_station_id)),
        ]

        for label, setup_fn in scenarios:
            snapshot = system.clone()
            setup_fn(snapshot)
            snapshot.fast_forward(duration_ms)
            total_boarded = sum(
                station.total_boarded
                for station in snapshot.stations.values()
            )
            max_crowd = max(
                station.max_waiting
                for station in snapshot.stations.values()
            )
            results[label] = {
                "total_boarded": total_boarded,
                "max_crowd": max_crowd,
            }

        max_boarded = max(item["total_boarded"] for item in results.values()) or 1
        max_crowd = max(item["max_crowd"] for item in results.values()) or 1
        scores = {
            label: (
                0.6 * values["total_boarded"] / max_boarded
                - 0.4 * values["max_crowd"] / max_crowd
            )
            for label, values in results.items()
        }
        best = max(scores, key=scores.get)
        return {"results": results, "scores": scores, "best": best}

