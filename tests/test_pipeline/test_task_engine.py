import numpy as np

from aoi_system.core.context import InspectionContext
from aoi_system.pipeline.runner import TaskPipelineRunner
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask
from aoi_system.pipeline.tasks.registry import TaskRegistry


class DummyThresholdTask(VisionTask):
    task_type = "dummy_threshold"

    def __init__(self, task_id: str = "thresh_1", threshold: int = 128, enabled: bool = True):
        super().__init__(task_id=task_id, task_type=self.task_type, enabled=enabled)
        self.threshold = threshold

    def run(self, ctx: InspectionContext) -> TaskResult:
        raw = ctx.get_image("raw")
        if raw is None:
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=False,
                elapsed_ms=0.0,
                message="No raw image",
            )
        binary = (raw > self.threshold).astype(np.uint8) * 255
        ctx.set_image("bin_out", binary)
        ctx.set_feature("white_pixels", int(np.sum(binary > 0)))
        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            elapsed_ms=0.0,
            message="OK",
        )


def test_inspection_context_blackboard():
    raw_img = np.zeros((100, 100), dtype=np.uint8)
    ctx = InspectionContext(slot_index=0, raw_image=raw_img)

    # Test images dictionary
    assert ctx.get_image("raw") is not None
    assert ctx.get_image("missing") is None

    bin_img = np.ones((100, 100), dtype=np.uint8) * 255
    ctx.set_image("bin", bin_img)
    assert ctx.get_image("bin") is not None

    # Test features dictionary
    ctx.set_feature("corner_anchor", (10, 20))
    assert ctx.get_feature("corner_anchor") == (10, 20)
    assert ctx.get_feature("nonexistent", default=None) is None

    # Test measurements dictionary
    ctx.set_measurement("L1", 25.4)
    assert ctx.get_measurement("L1") == 25.4
    assert ctx.get_measurement("L2") is None

    # Test anomalies
    ctx.add_anomaly("Edge blur detected")
    assert len(ctx.anomalies) == 1
    assert "Edge blur detected" in ctx.anomalies[0]


def test_vision_task_execution_and_timing():
    TaskRegistry.register("dummy_threshold", DummyThresholdTask)

    raw_img = np.zeros((50, 50), dtype=np.uint8)
    raw_img[10:40, 10:40] = 200
    ctx = InspectionContext(slot_index=1, raw_image=raw_img)

    task = TaskRegistry.create("dummy_threshold", task_id="t1", threshold=100)
    res = task.execute(ctx)

    assert res.success is True
    assert res.task_id == "t1"
    assert res.elapsed_ms >= 0.0
    assert ctx.get_image("bin_out") is not None
    assert ctx.get_feature("white_pixels") == 30 * 30
    assert "t1" in ctx.execution_stats


def test_task_pipeline_runner():
    raw_img = np.zeros((50, 50), dtype=np.uint8)
    raw_img[:25, :] = 255
    ctx = InspectionContext(slot_index=0, raw_image=raw_img)

    task1 = DummyThresholdTask(task_id="step1", threshold=100)
    task2 = DummyThresholdTask(task_id="step2_disabled", threshold=50, enabled=False)

    runner = TaskPipelineRunner(tasks=[task1, task2])
    results = runner.execute(ctx)

    assert len(results) == 1  # Only enabled task executed
    assert results[0].task_id == "step1"
    assert results[0].success is True
    assert ctx.get_feature("white_pixels") == 25 * 50
