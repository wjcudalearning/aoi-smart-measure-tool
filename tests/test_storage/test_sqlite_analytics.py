import json
import time
from pathlib import Path

import pytest

from aoi_system.storage.database.analytics import QualityAnalyticsService
from aoi_system.storage.database.models import InspectionRecordModel
from aoi_system.storage.database.sqlite_db import SqliteInspectionDatabase
from aoi_system.storage.exporter import ReportExporter


class TestSqliteAndAnalytics:
    def test_sqlite_sync_and_query(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test_inspections.db"
        db = SqliteInspectionDatabase(db_path=db_path)

        rec1 = InspectionRecordModel(
            timestamp="2026-09-17T12:00:00",
            slot_index=0,
            recipe_name="Part_A",
            overall_grade="A",
            execution_time_ms=1.85,
            measurements_json=json.dumps({"length": 25.02, "width": 10.01}),
            anomalies_json="[]",
        )
        rec2 = InspectionRecordModel(
            timestamp="2026-09-17T12:01:00",
            slot_index=1,
            recipe_name="Part_A",
            overall_grade="NG",
            execution_time_ms=2.10,
            measurements_json=json.dumps({"length": 26.50, "width": 9.20}),
            anomalies_json='["Length exceeds limit"]',
        )

        id1 = db.insert_record_sync(rec1)
        id2 = db.insert_record_sync(rec2)
        assert id1 > 0
        assert id2 > id1

        # Query all
        all_recs = db.query_records()
        assert len(all_recs) == 2

        # Filter by slot
        slot0_recs = db.query_records(slot_index=0)
        assert len(slot0_recs) == 1
        assert slot0_recs[0].overall_grade == "A"

        # Filter by grade
        ng_recs = db.query_records(grade="NG")
        assert len(ng_recs) == 1
        assert ng_recs[0].slot_index == 1

        db.close()

    def test_sqlite_async_queue(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test_async.db"
        db = SqliteInspectionDatabase(db_path=db_path)

        for i in range(10):
            db.insert_record_async(
                InspectionRecordModel(
                    timestamp=f"2026-09-17T12:00:{i:02d}",
                    slot_index=i % 3,
                    recipe_name="Batch_1",
                    overall_grade="A" if i % 4 != 0 else "NG",
                    execution_time_ms=1.5 + i * 0.1,
                    measurements_json="{}",
                    anomalies_json="[]",
                )
            )

        # Wait for queue to flush
        time.sleep(0.1)
        db.close()

        # Reopen to verify all 10 records were persisted
        db_verify = SqliteInspectionDatabase(db_path=db_path)
        recs = db_verify.query_records(limit=50)
        assert len(recs) == 10
        db_verify.close()

    def test_quality_analytics_service(self) -> None:
        svc = QualityAnalyticsService()

        # 1. Yield statistics
        records = [
            InspectionRecordModel(
                timestamp="2026-09-17T10:00:00",
                slot_index=0,
                recipe_name="R1",
                overall_grade="A",
                execution_time_ms=1.0,
                measurements_json="{}",
                anomalies_json="[]",
            ),
            InspectionRecordModel(
                timestamp="2026-09-17T10:01:00",
                slot_index=0,
                recipe_name="R1",
                overall_grade="A",
                execution_time_ms=1.0,
                measurements_json="{}",
                anomalies_json="[]",
            ),
            InspectionRecordModel(
                timestamp="2026-09-17T10:02:00",
                slot_index=0,
                recipe_name="R1",
                overall_grade="B",
                execution_time_ms=1.0,
                measurements_json="{}",
                anomalies_json="[]",
            ),
            InspectionRecordModel(
                timestamp="2026-09-17T10:03:00",
                slot_index=0,
                recipe_name="R1",
                overall_grade="NG",
                execution_time_ms=1.0,
                measurements_json="{}",
                anomalies_json="[]",
            ),
        ]
        stats = svc.calculate_yield_stats(records)
        assert stats["total"] == 4
        assert stats["count_A"] == 2
        assert stats["count_B"] == 1
        assert stats["count_NG"] == 1
        assert stats["yield_rate"] == 0.75  # (A+B)/Total

        # 2. Process Capability (CPK / PPK)
        # Perfectly centered data around 25.0 with std = 0.1, limits [24.7, 25.3]
        values = [24.9, 25.0, 25.1, 25.0, 24.95, 25.05, 25.0, 25.0]
        capability = svc.calculate_process_capability(values, usl=25.3, lsl=24.7)
        assert capability["cp"] > 1.0
        assert capability["cpk"] > 1.0
        assert capability["mean"] == pytest.approx(25.0, abs=0.05)

        # 3. Histogram bins
        bin_edges, counts = svc.calculate_histogram(values, bins=5)
        assert len(bin_edges) == 6
        assert len(counts) == 5
        assert sum(counts) == len(values)

    def test_report_exporter(self, tmp_path: Path) -> None:
        exporter = ReportExporter()
        records = [
            InspectionRecordModel(
                record_id=1,
                timestamp="2026-09-17T12:00:00",
                slot_index=0,
                recipe_name="Part_X",
                overall_grade="A",
                execution_time_ms=2.5,
                measurements_json=json.dumps({"dim1": 12.34}),
                anomalies_json="[]",
            )
        ]

        csv_file = tmp_path / "report.csv"
        out_csv = exporter.export_to_csv(records, csv_file)
        assert out_csv.exists()
        content = out_csv.read_text(encoding="utf-8")
        assert "Part_X" in content
        assert "GRADE_A" in content or "A" in content

        excel_file = tmp_path / "report.xlsx"
        out_excel = exporter.export_to_excel(records, excel_file)
        assert out_excel.exists()
