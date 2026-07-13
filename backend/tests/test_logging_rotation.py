"""
Log rotation (BUG-30) — fresh file per startup + daily rotation + bounded retention,
mirroring the sibling locveil-bridge scheme.
"""

import logging
import os
import time
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import pytest

from locveil_voice.utils.logging import (
    LOG_RETENTION_DAYS,
    _prune_old_logs,
    _startup_rollover,
    setup_logging,
)
from locveil_voice.config.models import LogLevel


def _teardown_root_handlers():
    root = logging.getLogger()
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)


class TestStartupRollover:
    def test_nonempty_log_renamed_into_sibling_family(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        log_file.write_text("Previous log content\n")

        _startup_rollover(log_file)

        assert not log_file.exists()
        rotated = list(tmp_path.glob("locveil_voice.log.*.log"))
        assert len(rotated) == 1
        assert rotated[0].read_text() == "Previous log content\n"
        # Stamp parses as YYYYMMDD_HHMMSS
        stamp = rotated[0].name[len("locveil_voice.log."):-len(".log")]
        datetime.strptime(stamp, "%Y%m%d_%H%M%S")

    def test_empty_log_reused_not_rotated(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        log_file.write_text("")

        _startup_rollover(log_file)

        assert log_file.exists()
        assert list(tmp_path.glob("locveil_voice.log.*.log")) == []

    def test_missing_log_is_noop(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        _startup_rollover(log_file)
        assert not log_file.exists()
        assert list(tmp_path.glob("locveil_voice.log.*")) == []


class TestPrune:
    def test_old_siblings_removed_recent_kept(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        old = tmp_path / "locveil_voice.log.20200101.log"
        recent = tmp_path / "locveil_voice.log.20991231_120000.log"
        old.write_text("old")
        recent.write_text("recent")
        past = time.time() - (LOG_RETENTION_DAYS + 5) * 86400
        os.utime(old, (past, past))

        removed = _prune_old_logs(log_file)

        assert removed == 1
        assert not old.exists()
        assert recent.exists()

    def test_live_file_never_pruned(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        log_file.write_text("live")
        past = time.time() - (LOG_RETENTION_DAYS + 5) * 86400
        os.utime(log_file, (past, past))

        _prune_old_logs(log_file)

        assert log_file.exists()  # glob is `<name>.*` — the live file is not a sibling


class TestSetupLogging:
    def test_rotates_previous_and_installs_timed_handler(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        log_file.write_text("Old log entry\n")

        try:
            setup_logging(level=LogLevel.INFO, log_file=log_file, enable_console=False)

            root = logging.getLogger()
            timed = [h for h in root.handlers if isinstance(h, TimedRotatingFileHandler)]
            assert len(timed) == 1
            handler = timed[0]
            assert handler.backupCount == LOG_RETENTION_DAYS
            assert handler.suffix == "%Y%m%d.log"
            # The cleanup regex must match the custom suffix, else backupCount deletes nothing
            assert handler.extMatch.match("20260708.log")

            logging.getLogger("bug30-test").info("fresh entry")
            handler.flush()

            assert "Old log entry" not in log_file.read_text()
            assert "fresh entry" in log_file.read_text()
            rotated = list(tmp_path.glob("locveil_voice.log.*.log"))
            assert len(rotated) == 1
            assert rotated[0].read_text() == "Old log entry\n"
        finally:
            _teardown_root_handlers()

    def test_prunes_expired_siblings_on_startup(self, tmp_path):
        log_file = tmp_path / "locveil_voice.log"
        expired = tmp_path / "locveil_voice.log.20200101.log"
        expired.write_text("ancient")
        past = time.time() - (LOG_RETENTION_DAYS + 5) * 86400
        os.utime(expired, (past, past))

        try:
            setup_logging(level=LogLevel.INFO, log_file=log_file, enable_console=False)
            assert not expired.exists()
        finally:
            _teardown_root_handlers()


if __name__ == "__main__":
    pytest.main([__file__])
