import inspect
from typing import Any

from aoi_system.pipeline.tasks.base import VisionTask


class TaskRegistry:
    """Registry and factory for pluggable vision tasks."""

    _registry: dict[str, type[VisionTask]] = {}

    @classmethod
    def register(cls, task_type: str, task_class: type[VisionTask]) -> None:
        cls._registry[task_type] = task_class

    @classmethod
    def create(
        cls,
        first_arg: str,
        second_arg: str | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> VisionTask:
        """Instantiates a registered vision task.

        Supports both:
        - `create(task_type, **kwargs)`
        - `create(task_id, task_type, params=dict)`
        """
        if second_arg is not None:
            task_id = first_arg
            task_type = second_arg
        else:
            task_type = first_arg
            task_id = kwargs.pop("task_id", task_type.lower())

        if task_type not in cls._registry:
            raise KeyError(f"Task type '{task_type}' is not registered in TaskRegistry.")

        task_cls = cls._registry[task_type]
        sig = inspect.signature(task_cls.__init__)
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

        call_args: dict[str, Any] = {}
        if "task_id" in sig.parameters or accepts_kwargs:
            call_args["task_id"] = task_id
        if "task_type" in sig.parameters or accepts_kwargs:
            call_args["task_type"] = task_type

        # Merge user params
        raw_kwargs = dict(kwargs)
        if params:
            raw_kwargs.update(params)

        for k, v in raw_kwargs.items():
            if k in sig.parameters or accepts_kwargs:
                call_args[k] = v

        return task_cls(**call_args)

    @classmethod
    def list_available_tasks(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
