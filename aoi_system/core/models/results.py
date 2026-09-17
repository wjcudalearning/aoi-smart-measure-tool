from pydantic import BaseModel, Field


class ContinuousInspectionRuleResult(BaseModel):
    rule_name: str
    calculation_value: str
    judgement: str  # "A", "B", "NG", or "N/A"


class ContinuousInspectionResult(BaseModel):
    slot_index: int = 0
    summary: str = "未設定條件"  # "A", "B", "NG", "未設定條件", "不可判斷"
    sub_parameter_name: str = ""
    rules: list[ContinuousInspectionRuleResult] = Field(default_factory=list)
    processing_time_ms: float = 0.0
