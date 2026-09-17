import ast
import math
import operator
import re
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from aoi_system.core.models.recipe import JudgementCriterionRule
from aoi_system.core.models.results import ContinuousInspectionRuleResult


class JudgementGrade(StrEnum):
    A = "A"
    B = "B"
    NG = "NG"
    NO_CONDITION = "未設定條件"
    UNJUDGEABLE = "不可判斷"


class JudgementEvaluator:
    """Safe AST-based math evaluator and industrial tolerance rule judgement engine."""

    _SAFE_OPERATORS: dict[type[ast.operator], Callable[..., Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }

    _SAFE_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[..., Any]] = {
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    _SAFE_FUNCTIONS: dict[str, Callable[..., Any]] = {
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sum": sum,
        "avg": lambda *args: sum(args) / len(args) if args else 0.0,
    }

    def evaluate_expression(self, expression: str, line_values: dict[int, float]) -> float | None:
        """Safely parses and evaluates mathematical expression.

        Supports line variables like (1) + (2).
        """
        if not expression or not expression.strip():
            return None

        expr = expression.strip()
        # Transform (1) to _v_1
        transformed = re.sub(r"\((\d+)\)", r"_v_\1", expr)
        variables: dict[str, float] = {f"_v_{k}": float(v) for k, v in line_values.items()}

        try:
            tree = ast.parse(transformed, mode="eval")
            return float(self._eval_node(tree.body, variables))
        except Exception:
            return None

    def _eval_node(self, node: ast.AST, variables: dict[str, float]) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant: {node.value!r}")

        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            if node.id in self._SAFE_FUNCTIONS:
                return self._SAFE_FUNCTIONS[node.id]
            raise NameError(f"Undefined variable: {node.id}")

        if isinstance(node, ast.BinOp):
            bin_op_type = type(node.op)
            if bin_op_type in self._SAFE_OPERATORS:
                left = self._eval_node(node.left, variables)
                right = self._eval_node(node.right, variables)
                return self._SAFE_OPERATORS[bin_op_type](left, right)
            raise ValueError(f"Unsupported operator: {bin_op_type}")

        if isinstance(node, ast.UnaryOp):
            unary_op_type = type(node.op)
            if unary_op_type in self._SAFE_UNARY_OPERATORS:
                operand = self._eval_node(node.operand, variables)
                return self._SAFE_UNARY_OPERATORS[unary_op_type](operand)
            raise ValueError(f"Unsupported unary operator: {unary_op_type}")

        if isinstance(node, ast.Call):
            func_node = node.func
            if isinstance(func_node, ast.Name) and func_node.id in self._SAFE_FUNCTIONS:
                func = self._SAFE_FUNCTIONS[func_node.id]
                args = [self._eval_node(arg, variables) for arg in node.args]
                return func(*args)
            raise ValueError("Unsupported function call in formula")

        raise TypeError(f"Unsupported syntax: {type(node).__name__}")

    def check_spec(self, value: float, spec_expression: str) -> bool:
        """Evaluates whether a value satisfies tolerance spec criteria."""
        if not spec_expression or not spec_expression.strip():
            return True

        spec = spec_expression.strip().replace(" ", "")

        # 1. Plus-minus tolerance: e.g. 10.0+-0.5 or 10.0±0.5
        pm_match = re.match(r"^([+-]?\d+(?:\.\d+)?)(?:\+\-|±)([+-]?\d+(?:\.\d+)?)$", spec)
        if pm_match:
            center = float(pm_match.group(1))
            tol = abs(float(pm_match.group(2)))
            return (center - tol) <= value <= (center + tol)

        # 2. Range: e.g. 10.0~20.0
        if "~" in spec:
            parts = spec.split("~", 1)
            try:
                lower = float(parts[0]) if parts[0] else float("-inf")
                upper = float(parts[1]) if parts[1] else float("inf")
                return lower <= value <= upper
            except ValueError:
                return False

        # 3. Comparison operators: >=, <=, >, <, =
        comp_match = re.match(r"^(>=|<=|>|<|=)?([+-]?\d+(?:\.\d+)?)$", spec)
        if comp_match:
            op = comp_match.group(1) or "="
            limit = float(comp_match.group(2))
            if op == ">=":
                return value >= limit
            if op == "<=":
                return value <= limit
            if op == ">":
                return value > limit
            if op == "<":
                return value < limit
            if op == "=":
                return math.isclose(value, limit, abs_tol=1e-5)

        return False

    def evaluate_rules(
        self, rules: list[JudgementCriterionRule], line_values: dict[int, float]
    ) -> tuple[JudgementGrade, list[ContinuousInspectionRuleResult]]:
        """Evaluates all rules for continuous inspection and computes final grade."""
        if not rules:
            return JudgementGrade.NO_CONDITION, []

        rule_results: list[ContinuousInspectionRuleResult] = []
        any_ng = False
        any_b = False

        for rule in rules:
            val_a = self.evaluate_expression(rule.calc_expression, line_values)
            val_str = f"{val_a:.4f}" if val_a is not None else "N/A"

            grade = "NG"
            if val_a is not None and self.check_spec(val_a, rule.spec_expression):
                grade = "A"
            else:
                # Check B criteria
                calc_b_expr = rule.calc_expression_b or rule.calc_expression
                val_b = (
                    self.evaluate_expression(calc_b_expr, line_values)
                    if calc_b_expr != rule.calc_expression
                    else val_a
                )
                if (
                    val_b is not None
                    and rule.spec_expression_b
                    and self.check_spec(val_b, rule.spec_expression_b)
                ):
                    grade = "B"
                else:
                    grade = "NG"

            if grade == "NG":
                any_ng = True
            elif grade == "B":
                any_b = True

            rule_results.append(
                ContinuousInspectionRuleResult(
                    rule_name=rule.name,
                    calculation_value=val_str,
                    judgement=grade,
                )
            )

        if any_ng:
            final_summary = JudgementGrade.NG
        elif any_b:
            final_summary = JudgementGrade.B
        else:
            final_summary = JudgementGrade.A

        return final_summary, rule_results
