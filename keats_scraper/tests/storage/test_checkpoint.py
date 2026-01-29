"""Tests for CheckpointManager."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from storage.checkpoint import CheckpointManager, ScrapingProgress
from utils.exceptions import CheckpointError


class TestScrapingProgress:
    """Tests for ScrapingProgress dataclass."""

    def test_new_sets_timestamps(self):
        """Test new() sets started_at and last_updated."""
        progress = ScrapingProgress.new()
        assert progress.started_at is not None
        assert progress.last_updated is not None

    def test_new_timestamps_are_iso_format(self):
        """Test timestamps are ISO format strings."""
        progress = ScrapingProgress.new()
        # Should be parseable as ISO datetime
        datetime.fromisoformat(progress.started_at)
        datetime.fromisoformat(progress.last_updated)

    def test_new_initializes_empty_lists(self):
        """Test new() initializes empty URL lists."""
        progress = ScrapingProgress.new()
        assert progress.processed_urls == []
        assert progress.failed_urls == []

    def test_new_sets_total_resources(self):
        """Test new() sets total_resources."""
        progress = ScrapingProgress.new(total_resources=100)
        assert progress.total_resources == 100

    def test_new_default_total_resources(self):
        """Test new() defaults total_resources to 0."""
        progress = ScrapingProgress.new()
        assert progress.total_resources == 0

    def test_new_documents_saved_zero(self):
        """Test new() sets documents_saved to 0."""
        progress = ScrapingProgress.new()
        assert progress.documents_saved == 0

    def test_new_current_section_empty(self):
        """Test new() sets current_section to empty string."""
        progress = ScrapingProgress.new()
        assert progress.current_section == ""


class TestCheckpointManagerInit:
    """Tests for CheckpointManager initialization."""

    def test_init_creates_directory(self, tmp_path):
        """Test checkpoint directory is created."""
        checkpoint_dir = tmp_path / "checkpoints"
        manager = CheckpointManager(checkpoint_dir)
        assert checkpoint_dir.exists()

    def test_init_sets_checkpoint_file(self, tmp_path):
        """Test checkpoint file path is set."""
        checkpoint_dir = tmp_path / "checkpoints"
        manager = CheckpointManager(checkpoint_dir)
        assert manager.checkpoint_file == checkpoint_dir / "progress.json"

    def test_init_progress_is_none(self, tmp_path):
        """Test _progress is initially None."""
        checkpoint_dir = tmp_path / "checkpoints"
        manager = CheckpointManager(checkpoint_dir)
        assert manager._progress is None


class TestLoad:
    """Tests for load method."""

    def test_load_no_file_returns_none(self, tmp_path):
        """Test None returned when no checkpoint exists."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        result = manager.load()
        assert result is None

    def test_load_success(self, tmp_path):
        """Test successful checkpoint loading."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "progress.json"

        # Create checkpoint file
        data = {
            "started_at": "2024-01-01T10:00:00",
            "last_updated": "2024-01-01T11:00:00",
            "total_resources": 50,
            "processed_urls": ["http://url1", "http://url2"],
            "failed_urls": ["http://url3"],
            "current_section": "Section 1",
            "documents_saved": 2,
        }
        checkpoint_file.write_text(json.dumps(data))

        manager = CheckpointManager(checkpoint_dir)
        result = manager.load()

        assert result is not None
        assert result.total_resources == 50
        assert len(result.processed_urls) == 2
        assert len(result.failed_urls) == 1

    def test_load_sets_internal_progress(self, tmp_path):
        """Test load sets _progress."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "progress.json"

        data = ScrapingProgress.new(10).__dict__
        data["started_at"] = str(data["started_at"])
        data["last_updated"] = str(data["last_updated"])
        checkpoint_file.write_text(json.dumps(data))

        manager = CheckpointManager(checkpoint_dir)
        manager.load()

        assert manager._progress is not None

    def test_load_invalid_json_returns_none(self, tmp_path):
        """Test None returned for invalid JSON."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "progress.json"
        checkpoint_file.write_text("invalid json {{{")

        manager = CheckpointManager(checkpoint_dir)
        result = manager.load()

        assert result is None


class TestSave:
    """Tests for save method."""

    def test_save_creates_file(self, tmp_path):
        """Test checkpoint file is created."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        progress = ScrapingProgress.new(10)
        manager.save(progress)

        assert manager.checkpoint_file.exists()

    def test_save_writes_json(self, tmp_path):
        """Test checkpoint file contains valid JSON."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        progress = ScrapingProgress.new(10)
        manager.save(progress)

        content = manager.checkpoint_file.read_text()
        data = json.loads(content)
        assert data["total_resources"] == 10

    def test_save_updates_last_updated(self, tmp_path):
        """Test last_updated is updated on save."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        progress = ScrapingProgress.new(10)
        old_updated = progress.last_updated

        # Wait a tiny bit
        import time
        time.sleep(0.01)

        manager.save(progress)

        # The progress object should have updated timestamp
        assert progress.last_updated != old_updated

    def test_save_sets_internal_progress(self, tmp_path):
        """Test save sets _progress."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        progress = ScrapingProgress.new(10)
        manager.save(progress)

        assert manager._progress is progress

    def test_save_raises_on_error(self, tmp_path, mocker):
        """Test CheckpointError on save failure."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        progress = ScrapingProgress.new(10)

        # Mock file write to fail
        mocker.patch.object(Path, "write_text", side_effect=IOError("Disk full"))

        with pytest.raises(CheckpointError):
            manager.save(progress)


class TestStartNew:
    """Tests for start_new method."""

    def test_start_new_creates_progress(self, tmp_path):
        """Test new progress is created."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        progress = manager.start_new(total_resources=25)

        assert isinstance(progress, ScrapingProgress)
        assert progress.total_resources == 25

    def test_start_new_saves_immediately(self, tmp_path):
        """Test progress is saved after creation."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(total_resources=25)

        assert manager.checkpoint_file.exists()

    def test_start_new_returns_progress(self, tmp_path):
        """Test start_new returns the progress object."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        result = manager.start_new(total_resources=50)

        assert result is not None
        assert result.total_resources == 50


class TestMarkProcessed:
    """Tests for mark_processed method."""

    def test_mark_processed_adds_url(self, tmp_path):
        """Test URL is added to processed list."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_processed("http://example.com/page1")

        assert "http://example.com/page1" in manager._progress.processed_urls

    def test_mark_processed_increments_count(self, tmp_path):
        """Test documents_saved is incremented."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_processed("http://example.com/page1")

        assert manager._progress.documents_saved == 1

    def test_mark_processed_no_duplicates(self, tmp_path):
        """Test same URL isn't added twice."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_processed("http://example.com/page1")
        manager.mark_processed("http://example.com/page1")

        assert manager._progress.processed_urls.count("http://example.com/page1") == 1
        assert manager._progress.documents_saved == 1

    def test_mark_processed_creates_progress_if_none(self, tmp_path):
        """Test progress is created if not exists."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.mark_processed("http://example.com/page1")

        assert manager._progress is not None
        assert "http://example.com/page1" in manager._progress.processed_urls

    def test_mark_processed_saves(self, tmp_path):
        """Test save is called after marking."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_processed("http://example.com/page1")

        # Reload and verify
        manager2 = CheckpointManager(tmp_path / "checkpoints")
        loaded = manager2.load()
        assert "http://example.com/page1" in loaded.processed_urls


class TestMarkFailed:
    """Tests for mark_failed method."""

    def test_mark_failed_adds_url(self, tmp_path):
        """Test URL is added to failed list."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_failed("http://example.com/page1")

        assert "http://example.com/page1" in manager._progress.failed_urls

    def test_mark_failed_no_duplicates(self, tmp_path):
        """Test same URL isn't added twice."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_failed("http://example.com/page1")
        manager.mark_failed("http://example.com/page1")

        assert manager._progress.failed_urls.count("http://example.com/page1") == 1

    def test_mark_failed_creates_progress_if_none(self, tmp_path):
        """Test progress is created if not exists."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.mark_failed("http://example.com/page1")

        assert manager._progress is not None
        assert "http://example.com/page1" in manager._progress.failed_urls

    def test_mark_failed_saves(self, tmp_path):
        """Test save is called after marking."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_failed("http://example.com/page1")

        # Reload and verify
        manager2 = CheckpointManager(tmp_path / "checkpoints")
        loaded = manager2.load()
        assert "http://example.com/page1" in loaded.failed_urls


class TestIsProcessed:
    """Tests for is_processed method."""

    def test_is_processed_true(self, tmp_path):
        """Test True for processed URL."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.mark_processed("http://example.com/page1")

        assert manager.is_processed("http://example.com/page1") is True

    def test_is_processed_false(self, tmp_path):
        """Test False for unprocessed URL."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)

        assert manager.is_processed("http://example.com/page1") is False

    def test_is_processed_no_progress(self, tmp_path):
        """Test False when no progress exists."""
        manager = CheckpointManager(tmp_path / "checkpoints")

        assert manager.is_processed("http://example.com/page1") is False


class TestUpdateSection:
    """Tests for update_section method."""

    def test_update_section_sets_value(self, tmp_path):
        """Test section is updated."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.update_section("New Section")

        assert manager._progress.current_section == "New Section"

    def test_update_section_saves(self, tmp_path):
        """Test save is called after update."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(5)
        manager.update_section("New Section")

        # Reload and verify
        manager2 = CheckpointManager(tmp_path / "checkpoints")
        loaded = manager2.load()
        assert loaded.current_section == "New Section"

    def test_update_section_creates_progress_if_none(self, tmp_path):
        """Test progress is created if not exists."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.update_section("New Section")

        assert manager._progress is not None


class TestGetStats:
    """Tests for get_stats method."""

    def test_get_stats_no_session(self, tmp_path):
        """Test 'no session' status when no progress."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        stats = manager.get_stats()

        assert stats["status"] == "no session"

    def test_get_stats_with_progress(self, tmp_path):
        """Test all stats are returned."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(10)
        manager.mark_processed("http://url1")
        manager.mark_processed("http://url2")
        manager.mark_failed("http://url3")

        stats = manager.get_stats()

        assert "started_at" in stats
        assert "last_updated" in stats
        assert stats["total_resources"] == 10
        assert stats["processed"] == 2
        assert stats["failed"] == 1
        assert stats["documents_saved"] == 2

    def test_get_stats_remaining_calculation(self, tmp_path):
        """Test remaining calculation is correct."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(10)
        manager.mark_processed("http://url1")
        manager.mark_processed("http://url2")
        manager.mark_failed("http://url3")

        stats = manager.get_stats()

        # remaining = total - processed - failed = 10 - 2 - 1 = 7
        assert stats["remaining"] == 7


class TestClear:
    """Tests for clear method."""

    def test_clear_deletes_file(self, tmp_path):
        """Test checkpoint file is deleted."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(10)
        assert manager.checkpoint_file.exists()

        manager.clear()

        assert not manager.checkpoint_file.exists()

    def test_clear_resets_progress(self, tmp_path):
        """Test _progress is set to None."""
        manager = CheckpointManager(tmp_path / "checkpoints")
        manager.start_new(10)
        assert manager._progress is not None

        manager.clear()

        assert manager._progress is None

    def test_clear_no_file(self, tmp_path):
        """Test no error when file doesn't exist."""
        manager = CheckpointManager(tmp_path / "checkpoints")

        # Should not raise
        manager.clear()

        assert manager._progress is None
