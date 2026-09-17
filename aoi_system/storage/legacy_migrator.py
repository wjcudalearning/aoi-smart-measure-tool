import re
from pathlib import Path

from pydantic import BaseModel, Field

from aoi_system.core.models.geometry import BoundingRect, Point2D, Point2I
from aoi_system.core.models.measurement import MeasureDirectionMode, MeasureRecord
from aoi_system.core.models.recipe import (
    CameraCalibration,
    DualThresholdSnapshot,
    InspectionRecipe,
    JudgementCriterionRule,
    ReferenceCornerPointMode,
)


class LegacyMigratorBundle(BaseModel):
    engineer_password: str = "0000"
    admin_password: str = "0000"
    list_sort_items: list[str] = Field(default_factory=list)
    main_parameters: dict[str, list[str]] = Field(default_factory=dict)
    recipes: dict[str, InspectionRecipe] = Field(default_factory=dict)


class LegacyIniMigrator:
    """Parses legacy C# INI configuration files.

    Transforms them into modern structured recipes.
    """

    def migrate_all(
        self,
        setting_path: Path | str,
        inner_setting_path: Path | str | None = None,
        param_ref_path: Path | str | None = None,
    ) -> LegacyMigratorBundle:
        bundle = LegacyMigratorBundle()

        # 1. Parse Camera Profiles (innerSetting.ini)
        camera_profiles: dict[int, CameraCalibration] = {}
        if inner_setting_path and Path(inner_setting_path).exists():
            camera_profiles = self._parse_inner_settings(Path(inner_setting_path))

        # 2. Parse Parameter Reference (parameterReferenceList.ini)
        sub_param_to_camera_idx: dict[str, int] = {}
        if param_ref_path and Path(param_ref_path).exists():
            bundle.main_parameters, sub_param_to_camera_idx = self._parse_param_references(
                Path(param_ref_path)
            )

        # 3. Parse Main Settings (setting.ini)
        if setting_path and Path(setting_path).exists():
            self._parse_settings(
                Path(setting_path), bundle, camera_profiles, sub_param_to_camera_idx
            )

        return bundle

    def _parse_inner_settings(self, path: Path) -> dict[int, CameraCalibration]:
        profiles: dict[int, CameraCalibration] = {}
        current_section = ""
        current_data: dict[str, str] = {}

        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                if current_section and current_section.lower().startswith("cameraprofile_"):
                    self._commit_camera_profile(current_section, current_data, profiles)
                current_section = line[1:-1].strip()
                current_data = {}
            elif "=" in line:
                k, v = line.split("=", 1)
                current_data[k.strip()] = v.strip()

        if current_section and current_section.lower().startswith("cameraprofile_"):
            self._commit_camera_profile(current_section, current_data, profiles)

        return profiles

    def _commit_camera_profile(
        self, section: str, data: dict[str, str], profiles: dict[int, CameraCalibration]
    ) -> None:
        try:
            idx = int(section.split("_")[-1])
            profiles[idx] = CameraCalibration(
                camera_name=data.get("CameraName", "DefaultCamera"),
                usage_name=data.get("UsageName", "Inspection"),
                ccd_x_precision=float(data.get("CcdXPrecision", 0.005)),
                ccd_y_precision=float(data.get("CcdYPrecision", 0.005)),
                measurement_scale_factor=float(data.get("MeasurementScaleFactor", 1.0)),
            )
        except ValueError:
            pass

    def _parse_param_references(self, path: Path) -> tuple[dict[str, list[str]], dict[str, int]]:
        main_params: dict[str, list[str]] = {}
        sub_camera_map: dict[str, int] = {}
        current_section = ""

        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
            elif "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if current_section.lower() == "subparameterinnersettings":
                    try:
                        sub_camera_map[k.upper()] = int(v)
                    except ValueError:
                        pass
                elif current_section.lower().startswith("subparameter_"):
                    main_name = current_section[len("subParameter_") :]
                    if main_name not in main_params:
                        main_params[main_name] = []
                    if v:
                        main_params[main_name].append(v)

        return main_params, sub_camera_map

    def _parse_settings(
        self,
        path: Path,
        bundle: LegacyMigratorBundle,
        camera_profiles: dict[int, CameraCalibration],
        sub_camera_map: dict[str, int],
    ) -> None:
        sections_data: dict[str, dict[str, str]] = {}
        current_section = ""

        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                if current_section not in sections_data:
                    sections_data[current_section] = {}
            elif "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if not current_section:
                    continue
                sections_data[current_section][k] = v

        # Passwords
        if "password" in sections_data:
            pw = sections_data["password"]
            bundle.engineer_password = pw.get("engineer", "0000")
            bundle.admin_password = pw.get("admin", "0000")

        # List sort
        if "listSort" in sections_data:
            for k, v in sections_data["listSort"].items():
                if v:
                    bundle.list_sort_items.append(v)

        # Parse product sections
        for section, kvs in sections_data.items():
            if section.lower() in ("password", "listsort"):
                continue

            product_key = section
            recipe = InspectionRecipe(product_key=product_key)
            cam_idx = sub_camera_map.get(product_key.upper(), 0)
            if cam_idx in camera_profiles:
                recipe.calibration = camera_profiles[cam_idx].model_copy()

            # Preprocess
            for i in range(1, 5):
                p_idx = i - 1
                prefix = f"Preprocess{i}"
                if f"{prefix}Enabled" in kvs:
                    recipe.preprocess_snapshots[p_idx].enabled = (
                        kvs.get(f"{prefix}Enabled", "false").lower() == "true"
                    )
                    recipe.preprocess_snapshots[p_idx].threshold = int(
                        kvs.get(f"{prefix}Threshold", "128")
                    )
                    recipe.preprocess_snapshots[p_idx].erode_iterations = int(
                        kvs.get(f"{prefix}Erode", "0")
                    )
                    recipe.preprocess_snapshots[p_idx].dilate_iterations = int(
                        kvs.get(f"{prefix}Dilate", "0")
                    )
                    recipe.preprocess_snapshots[p_idx].open_iterations = int(
                        kvs.get(f"{prefix}Open", "0")
                    )
                    recipe.preprocess_snapshots[p_idx].close_iterations = int(
                        kvs.get(f"{prefix}Close", "0")
                    )

            # Reference Corner
            if "ReferenceCornerEnabled" in kvs:
                recipe.reference_corner.enabled = (
                    kvs.get("ReferenceCornerEnabled", "false").lower() == "true"
                )
                recipe.reference_corner.source_index = int(kvs.get("ReferenceSourceIndex", "0"))
                recipe.reference_corner.point_mode = ReferenceCornerPointMode(
                    int(kvs.get("ReferencePointMode", "0"))
                )
                recipe.reference_corner.scan_line_threshold = int(
                    kvs.get("ReferenceScanLineThreshold", "128")
                )
                recipe.reference_corner.roi = BoundingRect(
                    x=int(kvs.get("ReferenceRoiX", "0")),
                    y=int(kvs.get("ReferenceRoiY", "0")),
                    width=int(kvs.get("ReferenceRoiWidth", "0")),
                    height=int(kvs.get("ReferenceRoiHeight", "0")),
                )
                recipe.reference_corner.roi_saved = (
                    kvs.get("ReferenceRoiSaved", "false").lower() == "true"
                )

            # Dual Threshold
            if "DualThresholdEnabled" in kvs:
                recipe.dual_threshold = DualThresholdSnapshot(
                    enabled=kvs.get("DualThresholdEnabled", "false").lower() == "true",
                    lower_threshold=int(kvs.get("DualThresholdLower", "50")),
                    upper_threshold=int(kvs.get("DualThresholdUpper", "200")),
                    erode_iterations=int(kvs.get("DualThresholdErode", "0")),
                    dilate_iterations=int(kvs.get("DualThresholdDilate", "0")),
                    open_iterations=int(kvs.get("DualThresholdOpen", "0")),
                    close_iterations=int(kvs.get("DualThresholdClose", "0")),
                )

            # Measure Records
            measure_indices = sorted(
                list({int(m.group(1)) for k in kvs if (m := re.match(r"^Measure(\d+)", k))})
            )
            for m_idx in measure_indices:
                p = f"Measure{m_idx}"
                dir_str = kvs.get(f"{p}Direction", "None").capitalize()
                dir_mode = MeasureDirectionMode.NONE
                if dir_str == "Parallel":
                    dir_mode = MeasureDirectionMode.PARALLEL
                elif dir_str == "Perpendicular":
                    dir_mode = MeasureDirectionMode.PERPENDICULAR

                record = MeasureRecord(
                    start_point=Point2I(
                        x=int(kvs.get(f"{p}X1", "0")), y=int(kvs.get(f"{p}Y1", "0"))
                    ),
                    end_point=Point2I(x=int(kvs.get(f"{p}X2", "0")), y=int(kvs.get(f"{p}Y2", "0"))),
                    center_point=Point2I(
                        x=int(kvs.get(f"{p}CenterX", "0")), y=int(kvs.get(f"{p}CenterY", "0"))
                    ),
                    local_start_point=Point2D(
                        x=float(kvs.get(f"{p}LocalX1", "0.0")),
                        y=float(kvs.get(f"{p}LocalY1", "0.0")),
                    ),
                    local_end_point=Point2D(
                        x=float(kvs.get(f"{p}LocalX2", "0.0")),
                        y=float(kvs.get(f"{p}LocalY2", "0.0")),
                    ),
                    distance=float(kvs.get(f"{p}Distance", "0.0")),
                    source_name=kvs.get(f"{p}Source", ""),
                    direction=dir_mode,
                    status_text=kvs.get(f"{p}Status", ""),
                )
                recipe.measure_records.append(record)

            # Judgement Criteria Rules
            judge_indices = sorted(
                list(
                    {
                        int(m.group(1))
                        for k in kvs
                        if (m := re.match(r"^JudgementCriterion(\d+)", k))
                    }
                )
            )
            for j_idx in judge_indices:
                p = f"JudgementCriterion{j_idx}"
                rule = JudgementCriterionRule(
                    name=kvs.get(f"{p}Name", ""),
                    calc_expression=kvs.get(f"{p}Calc", ""),
                    spec_expression=kvs.get(f"{p}Spec", ""),
                    calc_expression_b=kvs.get(f"{p}CalcB", ""),
                    spec_expression_b=kvs.get(f"{p}SpecB", ""),
                )
                recipe.judgement_rules.append(rule)

            bundle.recipes[product_key] = recipe
