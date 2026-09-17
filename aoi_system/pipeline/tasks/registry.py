from typing import Any

from aoi_system.pipeline.tasks.base import VisionTask


class TaskRegistry:
    """Registry and factory for pluggable vision tasks."""

    _registry: dict[str, type[VisionTask]] = {}

    @classmethod
    def register(cls, task_type: str, task_class: type[VisionTask]) -> None:
        cls._registry[task_type] = task_class

    @classmethod
    def create(cls, task_type: str, **kwargs: Any) -> VisionTask:
        if task_type not in cls._registry:
            raise KeyError(f"Task type '{task_type}' is not registered in TaskRegistry.")
        task_cls = cls._registry[task_type]
        return task_cls(**kwargs)

    @classmethod
    def list_available_tasks(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
