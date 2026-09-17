import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from aoi_system.core.models.recipe import InspectionRecipe
from aoi_system.core.models.results import ContinuousInspectionResult


@dataclass
class InspectionContext:
    """Carries frame data and metadata through the inspection pipeline with zero-copy."""

    slot_index: int
    image: np.ndarray
    recipe: InspectionRecipe | None = None
    source_name: str = ""
    timestamp: float = field(default_factory=time.time)
    result: ContinuousInspectionResult | None = None
    custom_data: dict[str, Any] = field(default_factory=dict)
