from aoi_system.pipeline.tasks.alignment_task import CornerAlignmentTask, TemplateMatchTask
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask
from aoi_system.pipeline.tasks.defect_task import BlobDefectTask
from aoi_system.pipeline.tasks.judgement_task import ToleranceJudgementTask
from aoi_system.pipeline.tasks.measurement_task import CircleFitTask, LineMeasureTask
from aoi_system.pipeline.tasks.plc_task import PlcPublishTask
from aoi_system.pipeline.tasks.preprocess_task import PreprocessTask
from aoi_system.pipeline.tasks.registry import TaskRegistry

# Auto-register standard vision operators
TaskRegistry.register("PreprocessTask", PreprocessTask)
TaskRegistry.register("CornerAlignmentTask", CornerAlignmentTask)
TaskRegistry.register("TemplateMatchTask", TemplateMatchTask)
TaskRegistry.register("LineMeasureTask", LineMeasureTask)
TaskRegistry.register("CircleFitTask", CircleFitTask)
TaskRegistry.register("BlobDefectTask", BlobDefectTask)
TaskRegistry.register("ToleranceJudgementTask", ToleranceJudgementTask)
TaskRegistry.register("PlcPublishTask", PlcPublishTask)

__all__ = [
    "BlobDefectTask",
    "CircleFitTask",
    "CornerAlignmentTask",
    "LineMeasureTask",
    "PlcPublishTask",
    "PreprocessTask",
    "TaskRegistry",
    "TaskResult",
    "TemplateMatchTask",
    "ToleranceJudgementTask",
    "VisionTask",
]
