import csv
from pathlib import Path

from aoi_system.storage.database.models import InspectionRecordModel


class ReportExporter:
    """Multi-format inspection history reporting engine (CSV and Excel formats)."""

    def export_to_csv(self, records: list[InspectionRecordModel], file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        headers = [
            "ID",
            "Timestamp",
            "Slot",
            "Recipe",
            "Grade",
            "ExecutionTimeMs",
            "Measurements",
            "Anomalies",
            "ImagePath",
        ]

        with open(path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in records:
                writer.writerow(
                    [
                        r.record_id or "",
                        r.timestamp,
                        r.slot_index,
                        r.recipe_name,
                        r.overall_grade,
                        r.execution_time_ms,
                        r.measurements_json,
                        r.anomalies_json,
                        r.image_path,
                    ]
                )
        return path

    def export_to_excel(self, records: list[InspectionRecordModel], file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Standard CSV fallback or openpyxl
        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            if ws is not None:
                ws.title = "Inspection History"
                headers = [
                    "ID",
                    "Timestamp",
                    "Slot",
                    "Recipe",
                    "Grade",
                    "ExecutionTimeMs",
                    "Measurements",
                    "Anomalies",
                    "ImagePath",
                ]
                ws.append(headers)
                for r in records:
                    ws.append(
                        [
                            r.record_id or "",
                            r.timestamp,
                            r.slot_index,
                            r.recipe_name,
                            r.overall_grade,
                            r.execution_time_ms,
                            r.measurements_json,
                            r.anomalies_json,
                            r.image_path,
                        ]
                    )
                wb.save(str(path))
                return path
        except ImportError:
            pass

        # Fallback to UTF-8-sig CSV format with .xlsx extension or copy
        return self.export_to_csv(records, path)
