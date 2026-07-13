"""
Logging Setup - Centralized logging configuration

Provides logging configuration for the entire Irene system.
"""

import logging
import re
import sys
import time
from datetime import datetime
from enum import Enum
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


class LogLevel(str, Enum):
    """Logging levels.

    ARCH-12: relocated here from `config.models` so the foundational `utils`
    layer no longer reaches up into `config`. `config.models` re-exports it for
    backward compatibility, so existing `from ..config.models import LogLevel`
    imports keep working.
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Rotation scheme (BUG-30): fresh file per startup + daily rotation + bounded retention —
# the same logic as the sibling locveil-bridge (`app/bootstrap.py::setup_logging`).
LOG_RETENTION_DAYS = 30


def _startup_rollover(log_path: Path) -> None:
    """Rename the previous run's live log aside so each startup begins a fresh file.

    The rotated name stays in the same `<name>.<stamp>.log` family the daily rotation
    uses, so the problem-report bundle's same-day glob sees both kinds of siblings.
    """
    if not log_path.exists():
        return
    try:
        if log_path.stat().st_size == 0:
            return  # nothing worth keeping; reuse the empty file
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = log_path.with_name(f"{log_path.name}.{stamp}.log")
        log_path.rename(rotated)
        # Log to console since file logging isn't set up yet
        print(f"Previous log rotated to: {rotated}")
    except OSError as e:
        # Never block startup on a rename failure
        print(f"Warning: could not rotate previous log {log_path}: {e}")


def _prune_old_logs(log_path: Path, keep_days: int = LOG_RETENTION_DAYS) -> int:
    """Delete rotated siblings (`<name>.*`) older than the retention window.

    Covers the startup-renamed files, which TimedRotatingFileHandler's own
    backupCount cleanup never matches (its extMatch only knows the daily suffix).
    """
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for sibling in log_path.parent.glob(log_path.name + ".*"):
        try:
            if sibling.stat().st_mtime < cutoff:
                sibling.unlink()
                removed += 1
        except OSError:
            continue
    return removed


class UTF8StreamHandler(logging.StreamHandler):
    """
    StreamHandler that ensures UTF-8 encoding for stdout/stderr.
    
    Addresses Windows terminal encoding issues by explicitly writing
    UTF-8 encoded bytes to the stream buffer when available.
    """

    def __init__(self, stream=None):
        super().__init__(stream)

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # If stream supports buffer (like sys.stdout), write UTF-8 encoded bytes
            if hasattr(stream, 'buffer'):
                stream.buffer.write(msg.encode('utf-8'))
                stream.buffer.write(self.terminator.encode('utf-8'))
                stream.buffer.flush()
            else:
                stream.write(msg + self.terminator)
                stream.flush()
        except Exception:
            self.handleError(record)


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    enable_console: bool = True
) -> None:
    """
    Set up logging for the Irene system.
    
    Args:
        level: Logging level
        log_file: Optional log file path
        enable_console: Whether to enable console logging
    """
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level.value)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler with UTF-8 support
    if enable_console:
        console_handler = UTF8StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler: fresh file per startup, daily rotation at midnight, bounded retention
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        _startup_rollover(log_file)
        _prune_old_logs(log_file)
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding='utf-8'
        )
        # Custom suffix for rotated files — and teach the handler's cleanup to
        # recognize it: getFilesToDelete() filters via extMatch, whose default
        # pattern never matches this suffix, so backupCount would delete nothing.
        file_handler.suffix = "%Y%m%d.log"
        file_handler.extMatch = re.compile(r"^\d{8}\.log$")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name) 