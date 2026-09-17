from pydantic import BaseModel, Field


class InspectionRecordModel(BaseModel):
    """Database model for storing historical workpiece inspection records."""

    record_id: int | None = Field(default=None, description="Primary auto-increment key")
    timestamp: str = Field(description="ISO 8601 formatted timestamp")
    slot_index: int = Field(default=0, description="Slot channel index 0, 1, or 2")
    recipe_name: str = Field(default="Default", description="Recipe model name")
    overall_grade: str = Field(default="NG", description="Final grade judgement A, B, or NG")
    execution_time_ms: float = Field(default=0.0, description="Pipeline total runtime in ms")
    measurements_json: str = Field(
        default="{}", description="Serialized JSON dictionary of measurements"
    )
    anomalies_json: str = Field(
        default="[]", description="Serialized JSON list of anomaly descriptions"
    )
    image_path: str = Field(default="", description="Optional saved frame filepath")
