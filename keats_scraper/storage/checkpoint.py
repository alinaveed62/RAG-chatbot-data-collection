"""Checkpoint management for resumable scraping."""

import json
from pathlib import Path
from datetime import datetime
from typing import Set, Optional, Dict, Any
from dataclasses import dataclass, asdict

from utils.logging_config import get_logger
from utils.exceptions import CheckpointError

logger = get_logger()


@dataclass
class ScrapingProgress:
    """Tracks scraping progress for resumption."""

    started_at: str
    last_updated: str
    total_resources: int
    processed_urls: list
    failed_urls: list
    current_section: str
    documents_saved: int

    @classmethod
    def new(cls, total_resources: int = 0) -> "ScrapingProgress":
        """Create new progress tracker."""
        now = datetime.utcnow().isoformat()
        return cls(
            started_at=now,
            last_updated=now,
            total_resources=total_resources,
            processed_urls=[],
            failed_urls=[],
            current_section="",
            documents_saved=0,
        )


class CheckpointManager:
    """Manages scraping checkpoints for resumption."""

    def __init__(self, checkpoint_dir: Path):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = checkpoint_dir / "progress.json"
        self._progress: Optional[ScrapingProgress] = None

    def load(self) -> Optional[ScrapingProgress]:
        """
        Load existing checkpoint.

        Returns:
            ScrapingProgress or None if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            logger.debug("No checkpoint found")
            return None

        try:
            data = json.loads(self.checkpoint_file.read_text())
            self._progress = ScrapingProgress(**data)
            logger.info(
                f"Loaded checkpoint: {len(self._progress.processed_urls)} URLs processed"
            )
            return self._progress

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def save(self, progress: ScrapingProgress) -> None:
        """
        Save checkpoint.

        Args:
            progress: Current scraping progress
        """
        try:
            progress.last_updated = datetime.utcnow().isoformat()
            self._progress = progress

            data = asdict(progress)
            self.checkpoint_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Checkpoint saved: {len(progress.processed_urls)} URLs")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise CheckpointError(f"Checkpoint save failed: {e}")

    def start_new(self, total_resources: int) -> ScrapingProgress:
        """
        Start a new scraping session.

        Args:
            total_resources: Total number of resources to process

        Returns:
            New ScrapingProgress
        """
        progress = ScrapingProgress.new(total_resources)
        self.save(progress)
        return progress

    def mark_processed(self, url: str) -> None:
        """
        Mark a URL as successfully processed.

        Args:
            url: Processed URL
        """
        if self._progress is None:
            self._progress = ScrapingProgress.new()

        if url not in self._progress.processed_urls:
            self._progress.processed_urls.append(url)
            self._progress.documents_saved += 1
            self.save(self._progress)

    def mark_failed(self, url: str) -> None:
        """
        Mark a URL as failed.

        Args:
            url: Failed URL
        """
        if self._progress is None:
            self._progress = ScrapingProgress.new()

        if url not in self._progress.failed_urls:
            self._progress.failed_urls.append(url)
            self.save(self._progress)

    def is_processed(self, url: str) -> bool:
        """
        Check if URL was already processed.

        Args:
            url: URL to check

        Returns:
            True if already processed
        """
        if self._progress is None:
            return False
        return url in self._progress.processed_urls

    def update_section(self, section: str) -> None:
        """
        Update current section being processed.

        Args:
            section: Section name
        """
        if self._progress is None:
            self._progress = ScrapingProgress.new()

        self._progress.current_section = section
        self.save(self._progress)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics.

        Returns:
            Dictionary of stats
        """
        if self._progress is None:
            return {"status": "no session"}

        return {
            "started_at": self._progress.started_at,
            "last_updated": self._progress.last_updated,
            "total_resources": self._progress.total_resources,
            "processed": len(self._progress.processed_urls),
            "failed": len(self._progress.failed_urls),
            "remaining": self._progress.total_resources
            - len(self._progress.processed_urls)
            - len(self._progress.failed_urls),
            "documents_saved": self._progress.documents_saved,
        }

    def clear(self) -> None:
        """Clear checkpoint data."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self._progress = None
        logger.info("Checkpoint cleared")
