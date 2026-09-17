import numpy as np
import pytest

from aoi_system.core.context import InspectionContext
from aoi_system.core.models.geometry import Point2D
from aoi_system.pipeline.tasks.alignment_task import CornerAlignmentTask, TemplateMatchTask
from aoi_system.pipeline.tasks.defect_task import BlobDefectTask
from aoi_system.pipeline.tasks.judgement_task import ToleranceJudgementTask
from aoi_system.pipeline.tasks.measurement_task import CircleFitTask, LineMeasureTask
from aoi_system.pipeline.tasks.plc_task import PlcPublishTask
from aoi_system.pipeline.tasks.preprocess_task import PreprocessTask
from aoi_system.pipeline.tasks.registry import TaskRegistry


class TestPluggableVisionTasks:
    @pytest.fixture
    def test_context(self) -> InspectionContext:
        ctx = InspectionContext(slot_index=0, frame_id=1)
        # Create a test image with a bright rectangle and a hole
        img = np.zeros((200, 200), dtype=np.uint8)
        img[40:160, 40:160] = 200
        # Simulated hole inside
        import cv2

        cv2.circle(img, (100, 100), 20, 0, -1)
        ctx.set_image("raw", img)
        return ctx

    def test_preprocess_task(self, test_context: InspectionContext) -> None:
        task = PreprocessTask(
            task_id="task_pre",
            input_image_key="raw",
            output_image_key="binary",
            threshold=150,
            upper_threshold=255,
        )
        res = task.execute(test_context)
        assert res.success is True
        assert "binary" in test_context.images
        binary = test_context.get_image("binary")
        assert binary is not None
        assert binary.shape == (200, 200)

    def test_corner_alignment_task(self, test_context: InspectionContext) -> None:
        # Preprocess first
        PreprocessTask(task_id="pre", threshold=150).execute(test_context)

        task = CornerAlignmentTask(
            task_id="task_align",
            input_image_key="binary",
            roi=(20, 20, 180, 180),
        )
        res = task.execute(test_context)
        assert res.success is True
        assert test_context.reference_basis is not None
        assert "reference_corner" in test_context.features

    def test_template_match_task(self, test_context: InspectionContext) -> None:
        # Create a 20x20 template from the center
        raw = test_context.get_image("raw")
        assert raw is not None
        template = raw[90:110, 90:110].copy()

        task = TemplateMatchTask(
            task_id="task_tpl",
            input_image_key="raw",
            template=template,
            min_score=0.8,
        )
        res = task.execute(test_context)
        assert res.success is True
        assert "template_match" in test_context.features

    def test_line_measure_task(self, test_context: InspectionContext) -> None:
        # Run corner alignment to set reference basis
        PreprocessTask(task_id="pre", threshold=150).execute(test_context)
        CornerAlignmentTask(task_id="align", input_image_key="binary").execute(test_context)

        task = LineMeasureTask(
            task_id="task_measure",
            param_name="width_1",
            point1=Point2D(x=50.0, y=50.0),
            point2=Point2D(x=150.0, y=50.0),
            pixel_size_mm=0.01,
        )
        res = task.execute(test_context)
        assert res.success is True
        assert "width_1" in test_context.measurements
        assert test_context.measurements["width_1"] == pytest.approx(1.0, abs=0.05)

    def test_circle_fit_task(self, test_context: InspectionContext) -> None:
        task = CircleFitTask(
            task_id="task_circle",
            input_image_key="raw",
            roi=(70, 70, 60, 60),  # around hole center (100, 100) with r=20
            pixel_size_mm=0.01,
        )
        res = task.execute(test_context)
        assert res.success is True
        assert "hole_diameter" in test_context.measurements

    def test_blob_defect_task(self, test_context: InspectionContext) -> None:
        PreprocessTask(task_id="pre", threshold=150).execute(test_context)
        task = BlobDefectTask(
            task_id="task_defect",
            input_image_key="binary",
            min_area=5,
            max_area=50000,
        )
        res = task.execute(test_context)
        assert res.success is True
        assert "defect_blobs" in test_context.features

    def test_tolerance_judgement_task(self, test_context: InspectionContext) -> None:
        test_context.set_measurement("width_1", 10.05)
        task = ToleranceJudgementTask(
            task_id="task_judge",
            rules=[
                {
                    "parameter_name": "width_1",
                    "spec": "9.9~10.1",
                }
            ],
        )
        res = task.execute(test_context)
        assert res.success is True
        assert test_context.overall_grade == "A"

    def test_plc_publish_task(self, test_context: InspectionContext) -> None:
        from unittest.mock import MagicMock

        from aoi_system.communication.modbus_client import ModbusTcpClient

        mock_modbus = MagicMock(spec=ModbusTcpClient)
        mock_modbus.publish_inspection_result.return_value = True

        task = PlcPublishTask(
            task_id="task_plc",
            modbus_client=mock_modbus,
        )
        test_context.overall_grade = "A"
        res = task.execute(test_context)
        assert res.success is True
        assert mock_modbus.publish_inspection_result.called

    def test_task_registry_reflection(self) -> None:
        # All standard vision tasks should be instantiable from TaskRegistry
        tasks = [
            ("PreprocessTask", {"threshold": 128}),
            ("CornerAlignmentTask", {}),
            ("TemplateMatchTask", {}),
            ("LineMeasureTask", {"param_name": "dim1"}),
            ("CircleFitTask", {}),
            ("BlobDefectTask", {}),
            ("ToleranceJudgementTask", {}),
            ("PlcPublishTask", {}),
        ]
        for t_type, params in tasks:
            task = TaskRegistry.create(f"id_{t_type}", t_type, params=params)
            assert task is not None
            assert task.task_type == t_type
