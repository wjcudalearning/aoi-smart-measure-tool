import queue
import sqlite3
import threading
from pathlib import Path
from typing import Any

from loguru import logger

from aoi_system.storage.database.models import InspectionRecordModel


class SqliteInspectionDatabase:
    """High-throughput SQLite database backend with zero-latency asynchronous write queue."""

    def __init__(self, db_path: str | Path = "inspections.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._queue: queue.Queue[InspectionRecordModel | None] = queue.Queue()
        self._is_running = True
        self._writer_thread = threading.Thread(target=self._async_writer_worker, daemon=True)
        self._init_schema()
        self._writer_thread.start()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inspection_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    slot_index INTEGER NOT NULL,
                    recipe_name TEXT NOT NULL,
                    overall_grade TEXT NOT NULL,
                    execution_time_ms REAL NOT NULL,
                    measurements_json TEXT NOT NULL,
                    anomalies_json TEXT NOT NULL,
                    image_path TEXT DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_records_time ON inspection_records(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_records_slot ON inspection_records(slot_index)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_records_grade ON inspection_records(overall_grade)"
            )
            conn.commit()

    def insert_record_async(self, record: InspectionRecordModel) -> None:
        """Enqueue record for non-blocking asynchronous persistence."""
        if self._is_running:
            self._queue.put(record)

    def insert_record_sync(self, record: InspectionRecordModel) -> int:
        """Synchronously inserts a single record and returns the assigned row ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inspection_records (
                    timestamp, slot_index, recipe_name, overall_grade,
                    execution_time_ms, measurements_json, anomalies_json, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.timestamp,
                    record.slot_index,
                    record.recipe_name,
                    record.overall_grade,
                    record.execution_time_ms,
                    record.measurements_json,
                    record.anomalies_json,
                    record.image_path,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def query_records(
        self,
        limit: int = 100,
        slot_index: int | None = None,
        grade: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[InspectionRecordModel]:
        conditions: list[str] = []
        params: list[Any] = []

        if slot_index is not None:
            conditions.append("slot_index = ?")
            params.append(slot_index)
        if grade is not None:
            conditions.append("overall_grade = ?")
            params.append(grade)
        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, timestamp, slot_index, recipe_name, overall_grade,
                   execution_time_ms, measurements_json, anomalies_json, image_path
            FROM inspection_records
            {where_clause}
            ORDER BY id DESC
            LIMIT ?
        """
        params.append(limit)

        results: list[InspectionRecordModel] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                results.append(
                    InspectionRecordModel(
                        record_id=row["id"],
                        timestamp=row["timestamp"],
                        slot_index=row["slot_index"],
                        recipe_name=row["recipe_name"],
                        overall_grade=row["overall_grade"],
                        execution_time_ms=row["execution_time_ms"],
                        measurements_json=row["measurements_json"],
                        anomalies_json=row["anomalies_json"],
                        image_path=row["image_path"],
                    )
                )
        return results

    def close(self) -> None:
        """Flushes write queue and closes database thread."""
        if not self._is_running:
            return

        self._is_running = False
        self._queue.put(None)
        if self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)
        logger.info("SqliteInspectionDatabase closed.")

    def _async_writer_worker(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        batch: list[InspectionRecordModel] = []

        while True:
            try:
                item = self._queue.get(timeout=0.05)
                if item is None:
                    break
                batch.append(item)
            except queue.Empty:
                pass

            if batch:
                try:
                    cursor.executemany(
                        """
                        INSERT INTO inspection_records (
                            timestamp, slot_index, recipe_name, overall_grade,
                            execution_time_ms, measurements_json, anomalies_json, image_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                r.timestamp,
                                r.slot_index,
                                r.recipe_name,
                                r.overall_grade,
                                r.execution_time_ms,
                                r.measurements_json,
                                r.anomalies_json,
                                r.image_path,
                            )
                            for r in batch
                        ],
                    )
                    conn.commit()
                except Exception as e:
                    logger.error(f"Error executing SQLite batch insert: {e}")
                batch.clear()

        conn.close()
