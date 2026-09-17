from typing import Any

from aoi_system.algorithms.preprocess.filters import PreprocessPipeline
from aoi_system.core.context import InspectionContext
from aoi_system.core.models.recipe import DualThresholdSnapshot, PreprocessSnapshot
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class PreprocessTask(VisionTask):
    """Vision task executing image thresholding and morphology preprocessing."""

    def __init__(
        self,
        task_id: str = "preprocess",
        task_type: str = "PreprocessTask",
        enabled: bool = True,
        input_image_key: str = "raw",
        output_image_key: str = "binary",
        threshold: float = 128.0,
        upper_threshold: float = 255.0,
        use_dual_threshold: bool = False,
        lower_threshold: int = 50,
        erode_iterations: int = 0,
        dilate_iterations: int = 0,
        open_iterations: int = 0,
        close_iterations: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.input_image_key = input_image_key
        self.output_image_key = output_image_key
        self.threshold = threshold
        self.upper_threshold = upper_threshold
        self.use_dual_threshold = use_dual_threshold
        self.lower_threshold = lower_threshold
        self.erode_iterations = erode_iterations
        self.dilate_iterations = dilate_iterations
        self.open_iterations = open_iterations
        self.close_iterations = close_iterations
        self._pipeline = PreprocessPipeline()

    def run(self, ctx: InspectionContext) -> TaskResult:
        img = ctx.get_image(self.input_image_key)
        if img is None:
            raise ValueError(
                f"Input image '{self.input_image_key}' not found in InspectionContext."
            )

        if self.use_dual_threshold:
            dual_cfg = DualThresholdSnapshot(
                enabled=True,
                lower_threshold=self.lower_threshold,
                upper_threshold=int(self.upper_threshold),
                erode_iterations=self.erode_iterations,
                dilate_iterations=self.dilate_iterations,
                open_iterations=self.open_iterations,
                close_iterations=self.close_iterations,
            )
            processed = self._pipeline.apply_dual_threshold(img, dual_cfg)
        else:
            prep_cfg = PreprocessSnapshot(
                enabled=True,
                threshold=int(self.threshold),
                upper_threshold=int(self.upper_threshold),
                use_dual_threshold=False,
                erode_iterations=self.erode_iterations,
                dilate_iterations=self.dilate_iterations,
                open_iterations=self.open_iterations,
                close_iterations=self.close_iterations,
            )
            processed = self._pipeline.apply_preprocess(img, prep_cfg)

        ctx.set_image(self.output_image_key, processed)
        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message=f"Image processed and saved as '{self.output_image_key}'",
            output_data={"shape": list(processed.shape)},
        )
