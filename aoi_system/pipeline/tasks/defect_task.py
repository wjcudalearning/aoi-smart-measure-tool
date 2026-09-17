from typing import Any

import cv2
import numpy as np

from aoi_system.core.context import InspectionContext
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class BlobDefectTask(VisionTask):
    """Vision task analyzing connected component blobs for surface defect detection."""

    def __init__(
        self,
        task_id: str = "blob_defect",
        task_type: str = "BlobDefectTask",
        enabled: bool = True,
        input_image_key: str = "binary",
        min_area: float = 10.0,
        max_area: float = 5000.0,
        defect_type: str = "Dark_or_Bright_Blob",
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.input_image_key = input_image_key
        self.min_area = min_area
        self.max_area = max_area
        self.defect_type = defect_type

    def run(self, ctx: InspectionContext) -> TaskResult:
        img = ctx.get_image(self.input_image_key)
        if img is None:
            raise ValueError(f"Image '{self.input_image_key}' not found in InspectionContext.")

        # Find connected components
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blobs: list[dict[str, Any]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if self.min_area <= area <= self.max_area:
                perimeter = cv2.arcLength(cnt, True)
                circularity = (
                    (4.0 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0.0
                )
                x, y, w, h = cv2.boundingRect(cnt)
                blobs.append(
                    {
                        "area": float(area),
                        "circularity": round(float(circularity), 3),
                        "bbox": [int(x), int(y), int(w), int(h)],
                    }
                )

        ctx.set_feature("defect_blobs", blobs)
        if blobs:
            msg = f"Detected {len(blobs)} defect blobs matching criteria."
            ctx.add_anomaly(msg)
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=True,
                message=msg,
                output_data={"blob_count": len(blobs)},
            )

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message="No defect blobs detected.",
            output_data={"blob_count": 0},
        )
