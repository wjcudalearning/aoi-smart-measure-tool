import sys
from pathlib import Path

from loguru import logger

from aoi_system.core.models.results import ContinuousInspectionResult


def setup_logging(log_dir: Path | str = "logs", level: str = "INFO") -> None:
    """Configures centralized asynchronous rotating logging using Loguru."""
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)

    logger.remove()

    # Console output
    log_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=log_fmt,
        level=level,
    )

    # General daily rotating log file
    logger.add(
        str(path / "aoi_system_{time:YYYY-MM-DD}.log"),
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        level=level,
        enqueue=True,
    )

    # Dedicated anomaly and NG event log file
    logger.add(
        str(path / "anomalies_{time:YYYY-MM-DD}.log"),
        filter=lambda rec: "ANOMALY" in rec["extra"] or rec["level"].name in ("ERROR", "CRITICAL"),
        rotation="00:00",
        retention="90 days",
        encoding="utf-8",
        enqueue=True,
    )


def log_inspection_anomaly(
    slot: int, result: ContinuousInspectionResult, details: str = ""
) -> None:
    """Records out-of-spec or inspection failure events."""
    if result.summary in ("NG", "不可判斷"):
        ng_rules = [r.rule_name for r in result.rules if r.judgement == "NG"]
        msg = (
            f"[Slot {slot}] Anomaly Detected: "
            f"Summary={result.summary}, FailedRules={ng_rules}. {details}"
        )
        logger.bind(ANOMALY=True).warning(msg)
