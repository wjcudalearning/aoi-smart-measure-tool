from typing import Any

import numpy as np

from aoi_system.storage.database.models import InspectionRecordModel


class QualityAnalyticsService:
    """Manufacturing quality analytics engine computing Yield, CPK, PPK, and distributions."""

    def calculate_yield_stats(self, records: list[InspectionRecordModel]) -> dict[str, Any]:
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "count_A": 0,
                "count_B": 0,
                "count_NG": 0,
                "yield_rate": 0.0,
                "ng_rate": 0.0,
            }

        count_a = sum(1 for r in records if r.overall_grade == "A")
        count_b = sum(1 for r in records if r.overall_grade == "B")
        count_ng = sum(1 for r in records if r.overall_grade == "NG")

        yield_rate = (count_a + count_b) / total
        ng_rate = count_ng / total

        return {
            "total": total,
            "count_A": count_a,
            "count_B": count_b,
            "count_NG": count_ng,
            "yield_rate": round(yield_rate, 4),
            "ng_rate": round(ng_rate, 4),
        }

    def calculate_process_capability(
        self, values: list[float], usl: float, lsl: float
    ) -> dict[str, float]:
        """Calculates statistical process capability indices (Cp, Cpk, Mean, Std)."""
        if len(values) < 2:
            return {
                "mean": float(np.mean(values)) if values else 0.0,
                "std": 0.0,
                "cp": 0.0,
                "cpk": 0.0,
                "cpu": 0.0,
                "cpl": 0.0,
            }

        arr = np.asarray(values, dtype=np.float64)
        mean = float(np.mean(arr))
        # Use ddof=1 for sample standard deviation
        std = float(np.std(arr, ddof=1))

        if std <= 1e-9:
            return {
                "mean": mean,
                "std": 0.0,
                "cp": 99.99,
                "cpk": 99.99,
                "cpu": 99.99,
                "cpl": 99.99,
            }

        cp = (usl - lsl) / (6.0 * std)
        cpu = (usl - mean) / (3.0 * std)
        cpl = (mean - lsl) / (3.0 * std)
        cpk = min(cpu, cpl)

        return {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "cp": round(cp, 4),
            "cpk": round(cpk, 4),
            "cpu": round(cpu, 4),
            "cpl": round(cpl, 4),
        }

    def calculate_histogram(
        self, values: list[float], bins: int = 10
    ) -> tuple[list[float], list[int]]:
        """Computes histogram bins and frequency counts."""
        if not values:
            return [], []

        arr = np.asarray(values, dtype=np.float64)
        counts, bin_edges = np.histogram(arr, bins=bins)
        return [float(e) for e in bin_edges], [int(c) for c in counts]
