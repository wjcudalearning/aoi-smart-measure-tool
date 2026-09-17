import tempfile
from pathlib import Path

from aoi_system.core.models.measurement import MeasureDirectionMode
from aoi_system.storage.legacy_migrator import LegacyIniMigrator

SAMPLE_SETTING_INI = """
[password]
engineer=1234
admin=8888

[listSort]
Item1=SUB_PROD_1
Item2=SUB_PROD_2

[SUB_PROD_1]
Preprocess1Enabled=True
Preprocess1Threshold=135
Preprocess1Erode=1
Preprocess1Dilate=2
Preprocess1Open=0
Preprocess1Close=1

ReferenceCornerEnabled=True
ReferenceSourceIndex=1
ReferencePointMode=0
ReferenceScanLineThreshold=140
ReferenceRoiX=15
ReferenceRoiY=25
ReferenceRoiWidth=200
ReferenceRoiHeight=150
ReferenceRoiSaved=True

Measure1X1=10
Measure1Y1=20
Measure1X2=50
Measure1Y2=60
Measure1CenterX=30
Measure1CenterY=40
Measure1LocalX1=5.5
Measure1LocalY1=12.3
Measure1LocalX2=45.2
Measure1LocalY2=18.9
Measure1Distance=25.432
Measure1Source=EdgeGap
Measure1Direction=Parallel
Measure1Status=PASS

JudgementCriterion1Name=TotalLength
JudgementCriterion1Calc=A+B
JudgementCriterion1Spec=20.0~30.0
JudgementCriterion1CalcB=A*2
JudgementCriterion1SpecB=18.0~32.0

DualThresholdEnabled=True
DualThresholdLower=40
DualThresholdUpper=210
DualThresholdErode=1
DualThresholdDilate=1
DualThresholdOpen=0
DualThresholdClose=0
"""

SAMPLE_INNER_SETTING_INI = """
[CameraProfile_0]
CameraName=TopBasler
UsageName=TopSurface
CcdXPrecision=0.0045
CcdYPrecision=0.0045
MeasurementScaleFactor=1.015
"""

SAMPLE_PARAM_REF_INI = """
[mainParameter]
Item1=MAIN_RECIPE_1

[subParameter_MAIN_RECIPE_1]
Sub1=SUB_PROD_1
Sub2=SUB_PROD_2
Sub3=

[subParameterInnerSettings]
SUB_PROD_1=0
"""


def test_legacy_ini_migrator():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        setting_file = tmp_path / "setting.ini"
        inner_file = tmp_path / "innerSetting.ini"
        ref_file = tmp_path / "parameterReferenceList.ini"

        setting_file.write_text(SAMPLE_SETTING_INI, encoding="utf-8")
        inner_file.write_text(SAMPLE_INNER_SETTING_INI, encoding="utf-8")
        ref_file.write_text(SAMPLE_PARAM_REF_INI, encoding="utf-8")

        migrator = LegacyIniMigrator()
        bundle = migrator.migrate_all(
            setting_path=setting_file, inner_setting_path=inner_file, param_ref_path=ref_file
        )

        # 1. Check Passwords
        assert bundle.engineer_password == "1234"
        assert bundle.admin_password == "8888"

        # 2. Check Recipes
        assert "SUB_PROD_1" in bundle.recipes
        recipe1 = bundle.recipes["SUB_PROD_1"]

        # Preprocess Snapshot 0
        prep0 = recipe1.preprocess_snapshots[0]
        assert prep0.enabled is True
        assert prep0.threshold == 135
        assert prep0.erode_iterations == 1
        assert prep0.dilate_iterations == 2

        # Reference Corner
        assert recipe1.reference_corner.enabled is True
        assert recipe1.reference_corner.roi.x == 15
        assert recipe1.reference_corner.roi.y == 25
        assert recipe1.reference_corner.roi.width == 200
        assert recipe1.reference_corner.roi.height == 150

        # Measurement Record
        assert len(recipe1.measure_records) == 1
        record = recipe1.measure_records[0]
        assert record.source_name == "EdgeGap"
        assert record.direction == MeasureDirectionMode.PARALLEL
        assert record.distance == 25.432
        assert record.start_point.x == 10
        assert record.start_point.y == 20
        assert record.end_point.x == 50
        assert record.end_point.y == 60

        # Judgement Rule
        assert len(recipe1.judgement_rules) == 1
        rule = recipe1.judgement_rules[0]
        assert rule.name == "TotalLength"
        assert rule.calc_expression == "A+B"
        assert rule.spec_expression == "20.0~30.0"

        # Camera Calibration mapping
        assert recipe1.calibration.camera_name == "TopBasler"
        assert recipe1.calibration.ccd_x_precision == 0.0045
        assert recipe1.calibration.measurement_scale_factor == 1.015

        # Dual Threshold
        assert recipe1.dual_threshold.enabled is True
        assert recipe1.dual_threshold.lower_threshold == 40
        assert recipe1.dual_threshold.upper_threshold == 210


def test_recipe_repository():
    from aoi_system.core.models.recipe import InspectionRecipe
    from aoi_system.storage.recipe_repository import RecipeRepository

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = RecipeRepository(storage_dir=tmpdir)
        recipe = InspectionRecipe(product_key="TEST_KEY")
        saved_path = repo.save(recipe)
        assert saved_path.exists()

        loaded = repo.load("TEST_KEY")
        assert loaded is not None
        assert loaded.product_key == "TEST_KEY"

        assert "TEST_KEY" in repo.list_all_keys()
        assert repo.load("NON_EXISTENT") is None
