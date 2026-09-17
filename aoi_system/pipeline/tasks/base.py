import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from aoi_system.core.context import InspectionContext


@dataclass
class TaskResult:
    """Standardized execution outcome for any vision task."""

    task_id: str
    task_type: str
    success: bool
    elapsed_ms: float = 0.0
    message: str = ""
    output_data: dict[str, Any] = field(default_factory=dict)


class VisionTask(ABC):
    """Abstract Base Class for pluggable vision operator tasks."""

    def __init__(self, task_id: str, task_type: str, enabled: bool = True) -> None:
        self.task_id = task_id
        self.task_type = task_type
        self.enabled = enabled

    @abstractmethod
    def run(self, ctx: InspectionContext) -> TaskResult:
        """Executes task logic reading inputs from and writing outputs to ctx."""
        raise NotImplementedError

    def execute(self, ctx: InspectionContext) -> TaskResult:
        """Executes task with automated profiling, exception isolation, and stats recording."""
        if not self.enabled:
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=True,
                elapsed_ms=0.0,
                message="Skipped (Disabled)",
            )

        t0 = time.perf_counter()
        try:
            result = self.run(ctx)
        except Exception as ex:
            elapsed = (time.perf_counter() - t0) * 1000.0
            err_msg = f"Task [{self.task_id}] failed with exception: {ex}"
            logger.error(err_msg)
            ctx.add_anomaly(err_msg)
            result = TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=False,
                elapsed_ms=elapsed,
                message=err_msg,
            )

        elapsed = (time.perf_counter() - t0) * 1000.0
        result.elapsed_ms = elapsed
        ctx.execution_stats[self.task_id] = elapsed
        return result
