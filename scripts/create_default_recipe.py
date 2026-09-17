"""Creates default and sample recipes for out-of-the-box verification and testing."""

from pathlib import Path

from aoi_system.core.models.geometry import BoundingRect, Point2I
from aoi_system.core.models.measurement import MeasureDirectionMode, MeasureRecord
from aoi_system.core.models.recipe import (
    CameraCalibration,
    InspectionRecipe,
    JudgementCriterionRule,
    PreprocessSnapshot,
    ReferenceCornerPointMode,
    ReferenceCornerSnapshot,
    VisionTaskConfig,
)
from aoi_system.storage.recipe_repository import RecipeRepository


def create_default_recipes(recipes_dir: str | Path = "recipes") -> None:
    repo = RecipeRepository(recipes_dir)

    # 1. Standard Workpiece Recipe
    recipe_standard = InspectionRecipe(product_key="STANDARD_WORKPIECE")
    recipe_standard.preprocess_snapshots[0] = PreprocessSnapshot(
        enabled=True,
        threshold=120,
        upper_threshold=255,
        close_iterations=1,
    )
    recipe_standard.reference_corner = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.CONTOUR_NEAREST,
        roi=BoundingRect(x=100, y=80, width=200, height=200),
    )
    recipe_standard.measure_records = [
        MeasureRecord(
            start_point=Point2I(x=100, y=200),
            end_point=Point2I(x=720, y=200),
            source_name="Preprocess 1",
            direction=MeasureDirectionMode.PARALLEL,
        ),
        MeasureRecord(
            start_point=Point2I(x=300, y=80),
            end_point=Point2I(x=300, y=480),
            source_name="Preprocess 1",
            direction=MeasureDirectionMode.PERPENDICULAR,
        ),
    ]

    recipe_standard.judgement_rules = [
        JudgementCriterionRule(
            name="Width_L1",
            calc_expression="(1)",
            spec_expression="24.50~25.50",
            calc_expression_b="(1)",
            spec_expression_b="24.00~26.00",
        ),
        JudgementCriterionRule(
            name="Height_L2",
            calc_expression="(2)",
            spec_expression="15.50~16.50",
            calc_expression_b="(2)",
            spec_expression_b="15.00~17.00",
        ),
    ]
    recipe_standard.calibration = CameraCalibration(
        ccd_x_precision=0.05,
        ccd_y_precision=0.05,
        measurement_scale_factor=1.0,
    )
    recipe_standard.tasks = [
        VisionTaskConfig(
            task_id="task_preprocess",
            task_type="PreprocessTask",
            parameters={"threshold": 120, "output_key": "binary_prep"},
        ),
        VisionTaskConfig(
            task_id="task_corner",
            task_type="CornerAlignmentTask",
            parameters={"roi": {"x": 100, "y": 80, "width": 200, "height": 200}},
        ),
        VisionTaskConfig(
            task_id="task_measure_width",
            task_type="LineMeasureTask",
            parameters={
                "start_x": 150,
                "start_y": 200,
                "end_x": 650,
                "end_y": 200,
                "measure_name": "Width_L1",
            },
        ),
        VisionTaskConfig(
            task_id="task_defect",
            task_type="BlobDefectTask",
            parameters={"min_area": 30, "max_area": 5000, "defect_name": "surface_blemish"},
        ),
        VisionTaskConfig(
            task_id="task_judge",
            task_type="ToleranceJudgementTask",
            parameters={
                "rules": [
                    {"name": "Width_L1", "spec": "24.50~25.50"},
                ]
            },
        ),
    ]
    repo.save(recipe_standard)

    # 2. Precision Connector Sample Recipe
    recipe_connector = InspectionRecipe(product_key="SAMPLE_CONNECTOR")
    recipe_connector.preprocess_snapshots[0] = PreprocessSnapshot(
        enabled=True,
        threshold=100,
        upper_threshold=255,
    )
    recipe_connector.reference_corner = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.CONTOUR_NEAREST,
        roi=BoundingRect(x=50, y=50, width=150, height=150),
    )
    recipe_connector.measure_records = [
        MeasureRecord(
            start_point=Point2I(x=80, y=100),
            end_point=Point2I(x=480, y=100),
            source_name="Preprocess 1",
            direction=MeasureDirectionMode.PARALLEL,
        )
    ]
    recipe_connector.judgement_rules = [
        JudgementCriterionRule(
            name="Pitch_Span",
            calc_expression="(1)",
            spec_expression="19.80~20.20",
        )
    ]
    recipe_connector.calibration = CameraCalibration(
        ccd_x_precision=0.05,
        ccd_y_precision=0.05,
        measurement_scale_factor=1.0,
    )
    repo.save(recipe_connector)


if __name__ == "__main__":
    create_default_recipes()
    print("Successfully created default recipes in recipes/")
