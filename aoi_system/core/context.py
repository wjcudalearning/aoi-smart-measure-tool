import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class InspectionContext:
    """Blackboard architecture carrying images, extracted features, and results across tasks."""

    slot_index: int = 0
    raw_image: np.ndarray | None = None
    timestamp: float = field(default_factory=time.time)
    images: dict[str, np.ndarray] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    measurements: dict[str, float] = field(default_factory=dict)
    rule_results: list[Any] = field(default_factory=list)
    summary: str = "未設定條件"
    anomalies: list[str] = field(default_factory=list)
    execution_stats: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.raw_image is not None and "raw" not in self.images:
            self.images["raw"] = self.raw_image

    def set_image(self, name: str, img: np.ndarray) -> None:
        self.images[name] = img

    def get_image(self, name: str) -> np.ndarray | None:
        return self.images.get(name)

    def set_feature(self, name: str, value: Any) -> None:
        self.features[name] = value

    def get_feature(self, name: str, default: Any = None) -> Any:
        return self.features.get(name, default)

    def set_measurement(self, name: str, value: float) -> None:
        self.measurements[name] = float(value)

    def get_measurement(self, name: str) -> float | None:
        return self.measurements.get(name)

    def add_anomaly(self, message: str) -> None:
        self.anomalies.append(message)
