from aoi_system.core.context import InspectionContext
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class TaskPipelineRunner:
    """Dispatches execution across an ordered sequence of vision tasks."""

    def __init__(self, tasks: list[VisionTask] | None = None) -> None:
        self.tasks: list[VisionTask] = tasks or []

    def add_task(self, task: VisionTask) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def clear_tasks(self) -> None:
        self.tasks.clear()

    def execute(self, ctx: InspectionContext) -> list[TaskResult]:
        """Executes all enabled tasks sequentially against the shared context."""
        results: list[TaskResult] = []
        for task in self.tasks:
            if not task.enabled:
                continue
            res = task.execute(ctx)
            results.append(res)
        return results
