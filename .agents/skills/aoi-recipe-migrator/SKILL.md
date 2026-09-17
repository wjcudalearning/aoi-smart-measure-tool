---
name: aoi-recipe-migrator
description: >-
  Inspect, parse, validate, and migrate legacy C# INI configuration files (setting.ini,
  parameterReferenceList.ini, innerSetting.ini) into modern structured JSON/SQLite recipes.
  Use whenever user needs to inspect existing recipes or convert legacy configurations.
---

# AOI Recipe Migrator Skill

This skill guides the inspection and lossless migration of legacy AOI product recipes.

## Legacy INI Structure Mapping

- **`setting.ini`**:
  - `[preprocess_{ProductKey}_{Index}]`: Threshold, UpperThreshold, DualThreshold, Erode, Dilate, Open, Close iterations.
  - `[referenceCorner_{ProductKey}]`: Enabled, SourceIndex, PointMode, ScanLineThreshold, Roi, CornerFound.
  - `[measure_{ProductKey}]`: Measure record points (Start, End, Center), Direction, Distance.
  - `[judgementCriteria_{ProductKey}]`: Formula expressions, Specs, Rules.
  - `[dualThreshold_{ProductKey}]`: Dual threshold configuration.
  - `[listSort]`: Shared sub-parameter list order.
  - `[password]`: Engineer & Admin passwords.
- **`parameterReferenceList.ini`**:
  - Main parameter definitions and their 3 associated sub-parameters.
  - `[subParameterInnerSettings]`: Mapping of sub-parameters to camera profile index.
- **`innerSetting.ini`**:
  - Camera profiles: `CcdXPrecision`, `CcdYPrecision`, `MeasurementScaleFactor`, `CameraName`, `UsageName`.

## Target Modern Schema

Target structure is a single unified `InspectionRecipe` object (stored in JSON or SQLite):
- `id`, `name`, `version`, `updated_at`
- `camera_config`: CCD precision, scale factor
- `preprocess`: GPU/CPU filter pipeline settings
- `corner_detection`: ROI, algorithm mode, scan threshold
- `measurements`: List of measurement items in local coordinate space
- `judgement_rules`: List of rules with safe expression grammar
