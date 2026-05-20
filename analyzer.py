from __future__ import annotations #타입 힌트 사용 우연화 관련. 코드와는 관계 X

from .simulation import Simulation
from .station import Station


class BottleneckAnalyzer:
    """Detects bottlenecks and compares treatment scenarios."""

    BOTTLENECK_THRESHOLD =30 #병목으로 판단하는 기준 인원

    #detect: 모든 역 리스트를 훑어서 병목인 역을 반환
    def detect(self, stations: dict[str, Station]) -> list[Station]:
        return [
            station
            for station in stations.values()
            if len(station) >= self.BOTTLENECK_THRESHOLD and not station.is_skipped
        ]

    #시나리오 분석 함수(로직 변경 -> 혼잡도에 따른 열차 지연 추가)
    def run_scenario(
        self,
        simulation: Simulation,
        target_station_id: str,
        duration_ms: int = 30000,
    ):
        results = {}
        scenarios = [
            ("현상유지", lambda snapshot: None),
            ("무정차 분산", lambda snapshot: snapshot.apply_skip(target_station_id)),
            ("열차 추가", lambda snapshot: snapshot.apply_extra_train(target_station_id)),
        ]
        
        for label, setup_fn in scenarios:
            snapshot = simulation.clone()
            setup_fn(snapshot)
            snapshot.fast_forward(duration_ms)

            # 1. 처리량 (승차 인원)
            total_boarded = sum(station.total_boarded for station in snapshot.stations.values())
            # 2. 시스템 건강도: 위험 수치를 초과한 역의 개수 (페널티)
            overloaded_stations = sum(1 for station in snapshot.stations.values() if len(station) > Station.OVERLOAD_THRESHOLD)
            # 3. 노선 흐름: 열차들이 이동한 총 누적 거리 (높을수록 지연 없이 잘 달렸다는 뜻)
            train_progress = sum(train.progress for train in snapshot.trains)
            
            results[label] = {
                "total_boarded": total_boarded,
                "overloaded_stations": overloaded_stations,
                "train_progress": train_progress,
            }
        
        max_boarded = max(item["total_boarded"] for item in results.values()) or 1
        max_progress = max(item["train_progress"] for item in results.values()) or 1
        
        # [새로운 점수 공식] 처리량 50% + 노선 흐름 40% - 과부하 페널티 
        scores = {
            label: (
                0.5 * (values["total_boarded"] / max_boarded)
                + 0.4 * (values["train_progress"] / max_progress)
                - 0.3 * values["overloaded_stations"]
            )
            for label, values in results.items()
        }

        best = max(scores, key=scores.get)
        return {"results": results, "scores": scores, "best": best}
