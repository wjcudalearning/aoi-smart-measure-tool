from typing import Any

from aoi_system.algorithms.judgement.evaluator import JudgementEvaluator
from aoi_system.core.context import InspectionContext
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class ToleranceJudgementTask(VisionTask):
    """Vision task executing safe AST expression evaluation for dimension tolerance grading."""

    def __init__(
        self,
        task_id: str = "tolerance_judgement",
        task_type: str = "ToleranceJudgementTask",
        enabled: bool = True,
        rules: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.raw_rules: list[dict[str, Any]] = rules or []
        self._evaluator = JudgementEvaluator()

    def run(self, ctx: InspectionContext) -> TaskResult:
        if not self.raw_rules:
            ctx.overall_grade = "A"
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=True,
                message="No judgement rules specified. Defaulting to grade A.",
                output_data={"overall_grade": "A"},
            )

        # Convert measurements to index map and name map
        val_map: dict[int, float] = {}
        for i, (k, v) in enumerate(ctx.measurements.items(), start=1):
            val_map[i] = v

        overall_grade = "A"
        results_list: list[dict[str, Any]] = []

        for idx, r in enumerate(self.raw_rules, start=1):
            param = r.get("parameter_name") or r.get("param_name") or f"({idx})"
            spec = r.get("spec_expression") or r.get("spec") or r.get("expression") or ""

            # Check if param matches a named measurement
            val: float | None = None
            if param in ctx.measurements:
                val = ctx.measurements[param]
            else:
                # Try evaluating as an expression
                val = self._evaluator.evaluate_expression(param, val_map)

            if val is not None:
                passed = self._evaluator.check_spec(val, spec)
                grade = "A" if passed else "NG"
            else:
                passed = False
                grade = "NG"

            if not passed:
                overall_grade = "NG"
                msg = f"Parameter [{param}]={val} failed spec [{spec}]"
                ctx.add_anomaly(msg)
            else:
                msg = f"Parameter [{param}]={val} passed spec [{spec}]"

            results_list.append(
                {"parameter": param, "value": val, "spec": spec, "passed": passed, "grade": grade}
            )

        ctx.overall_grade = overall_grade
        ctx.rule_results = results_list

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message=f"Tolerance evaluation finished: Overall Grade = {overall_grade}",
            output_data={"overall_grade": overall_grade, "details": results_list},
        )
