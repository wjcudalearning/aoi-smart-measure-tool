from typing import Any

from aoi_system.communication.modbus_client import ModbusTcpClient
from aoi_system.core.context import InspectionContext
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class PlcPublishTask(VisionTask):
    """Vision task publishing inspection grades and counts to line PLC via Modbus TCP."""

    def __init__(
        self,
        task_id: str = "plc_publish",
        task_type: str = "PlcPublishTask",
        enabled: bool = True,
        modbus_client: ModbusTcpClient | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.modbus_client = modbus_client

    def run(self, ctx: InspectionContext) -> TaskResult:
        grade = ctx.overall_grade or "NG"
        slot = ctx.slot_index

        if self.modbus_client is not None:
            success = self.modbus_client.publish_inspection_result(
                slot_index=slot, grade=grade, count=ctx.frame_id
            )
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=success,
                message=f"Published slot {slot} grade {grade} to PLC",
                output_data={"slot": slot, "grade": grade, "published": success},
            )

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message="No Modbus client attached; publication skipped.",
            output_data={"slot": slot, "grade": grade, "published": False},
        )
