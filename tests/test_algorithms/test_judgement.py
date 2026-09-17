from aoi_system.algorithms.judgement.evaluator import JudgementEvaluator, JudgementGrade
from aoi_system.core.models.recipe import JudgementCriterionRule


def test_evaluate_formula_basic():
    evaluator = JudgementEvaluator()
    line_values = {1: 12.5, 2: 7.5, 3: 5.0}

    # Addition
    val1 = evaluator.evaluate_expression("(1) + (2)", line_values)
    assert val1 == 20.0

    # Arithmetic with parentheses
    val2 = evaluator.evaluate_expression("((1) - (2)) * 2", line_values)
    assert val2 == 10.0

    # Max and Min functions
    val3 = evaluator.evaluate_expression("max((1), (2), (3))", line_values)
    assert val3 == 12.5
    val4 = evaluator.evaluate_expression("min((1), (2), (3))", line_values)
    assert val4 == 5.0


def test_check_spec_range():
    evaluator = JudgementEvaluator()
    assert evaluator.check_spec(15.0, "10.0~20.0") is True
    assert evaluator.check_spec(10.0, "10.0~20.0") is True
    assert evaluator.check_spec(20.0, "10.0~20.0") is True
    assert evaluator.check_spec(9.99, "10.0~20.0") is False
    assert evaluator.check_spec(20.01, "10.0~20.0") is False


def test_check_spec_tolerance():
    evaluator = JudgementEvaluator()
    # 15.0 +- 1.0 -> [14.0, 16.0]
    assert evaluator.check_spec(15.5, "15.0 +- 1.0") is True
    assert evaluator.check_spec(13.9, "15.0 +- 1.0") is False


def test_check_spec_comparisons():
    evaluator = JudgementEvaluator()
    assert evaluator.check_spec(15.0, "> 10") is True
    assert evaluator.check_spec(10.0, "> 10") is False
    assert evaluator.check_spec(10.0, ">= 10") is True
    assert evaluator.check_spec(5.0, "< 10") is True
    assert evaluator.check_spec(10.0, "<= 10") is True


def test_evaluate_rules_and_summary():
    evaluator = JudgementEvaluator()
    rules = [
        JudgementCriterionRule(
            name="Rule1",
            calc_expression="(1) + (2)",
            spec_expression="18.0~22.0",
            calc_expression_b="(1) + (2)",
            spec_expression_b="16.0~24.0",
        ),
        JudgementCriterionRule(
            name="Rule2",
            calc_expression="(3)",
            spec_expression="4.0~6.0",
            calc_expression_b="",
            spec_expression_b="",
        ),
    ]

    # 1. All A
    lines_all_a = {1: 10.0, 2: 10.0, 3: 5.0}
    summary, rule_results = evaluator.evaluate_rules(rules, lines_all_a)
    assert summary == JudgementGrade.A
    assert rule_results[0].judgement == "A"
    assert rule_results[1].judgement == "A"

    # 2. One B, No NG -> B
    lines_with_b = {1: 10.0, 2: 13.0, 3: 5.0}  # Rule1 sum = 23 (Outside A: 18~22, Inside B: 16~24)
    summary, rule_results = evaluator.evaluate_rules(rules, lines_with_b)
    assert summary == JudgementGrade.B
    assert rule_results[0].judgement == "B"
    assert rule_results[1].judgement == "A"

    # 3. One NG -> NG
    lines_with_ng = {1: 10.0, 2: 20.0, 3: 5.0}  # Rule1 sum = 30 (Outside B)
    summary, rule_results = evaluator.evaluate_rules(rules, lines_with_ng)
    assert summary == JudgementGrade.NG
    assert rule_results[0].judgement == "NG"
