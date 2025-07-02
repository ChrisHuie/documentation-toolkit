"""
Centralized checkpoint management for long-running operations.

This module provides a flexible checkpoint system that can save state
based on various strategies including time, progress, and rate limits.
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import get_logger


@dataclass
class CheckpointMetadata:
    """Metadata for checkpoint operations."""

    total_items: int | None = None
    processed_items: int = 0
    rate_limit_remaining: int | None = None
    rate_limit_total: int | None = None
    error_count: int = 0
    tool_name: str | None = None
    operation_type: str | None = None
    save_count: int = 0
    last_save_reason: str | None = None


@dataclass
class CheckpointData:
    """Standardized checkpoint data structure."""

    version: str = "2.0"
    operation_id: str
    state: dict[str, Any]
    metadata: CheckpointMetadata
    created_at: str
    last_updated: str

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointData":
        """Create CheckpointData from dictionary."""
        # Handle v1.0 format migration
        if "version" not in data or data.get("version") == "1.0":
            # Migrate old format
            return cls._migrate_v1_checkpoint(data)

        metadata = CheckpointMetadata(**data.get("metadata", {}))
        return cls(
            version=data["version"],
            operation_id=data["operation_id"],
            state=data["state"],
            metadata=metadata,
            created_at=data["created_at"],
            last_updated=data["last_updated"],
        )

    @classmethod
    def _migrate_v1_checkpoint(cls, data: dict) -> "CheckpointData":
        """Migrate v1.0 checkpoint format to v2.0."""
        # v1.0 format: {"files_data": {...}, "processed_files": [...], "timestamp": ...}
        state = {
            "files_data": data.get("files_data", {}),
            "processed_files": data.get("processed_files", []),
        }

        # Convert files_data from array to dict if needed
        if isinstance(state["files_data"], list):
            files_dict = {}
            for item in state["files_data"]:
                if isinstance(item, dict) and "path" in item:
                    files_dict[item["path"]] = ""
            state["files_data"] = files_dict

        metadata = CheckpointMetadata(
            processed_items=len(state.get("processed_files", [])),
            tool_name="github_client",
            operation_type="fetch_filenames",
        )

        timestamp = data.get("timestamp", time.time())
        created_at = datetime.fromtimestamp(timestamp).isoformat()

        return cls(
            version="2.0",
            operation_id="migrated_checkpoint",
            state=state,
            metadata=metadata,
            created_at=created_at,
            last_updated=created_at,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "operation_id": self.operation_id,
            "state": self.state,
            "metadata": asdict(self.metadata),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


@dataclass
class CheckpointContext:
    """Context information for checkpoint decisions."""

    processed_items: int = 0
    total_items: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_total: int | None = None
    elapsed_time: float = 0
    error_count: int = 0
    last_save_time: float = 0


class SaveStrategy(ABC):
    """Base class for checkpoint save strategies."""

    @abstractmethod
    def should_save(self, context: CheckpointContext) -> tuple[bool, str]:
        """
        Determine if checkpoint should be saved.

        Returns:
            Tuple of (should_save, reason)
        """
        pass


class TimeBasedStrategy(SaveStrategy):
    """Save checkpoint based on elapsed time."""

    def __init__(self, interval_seconds: int = 300):
        """Initialize with save interval in seconds."""
        self.interval = interval_seconds

    def should_save(self, context: CheckpointContext) -> tuple[bool, str]:
        """Save if enough time has elapsed since last save."""
        time_since_save = context.elapsed_time - context.last_save_time
        should_save = time_since_save >= self.interval
        reason = f"Time-based: {time_since_save:.0f}s >= {self.interval}s" if should_save else ""
        return should_save, reason


class ProgressBasedStrategy(SaveStrategy):
    """Save checkpoint based on items processed."""

    def __init__(self, items_interval: int = 1000):
        """Initialize with number of items between saves."""
        self.items_interval = items_interval
        self._last_saved_count = 0

    def should_save(self, context: CheckpointContext) -> tuple[bool, str]:
        """Save if enough items have been processed."""
        items_since_save = context.processed_items - self._last_saved_count
        should_save = items_since_save >= self.items_interval

        if should_save:
            self._last_saved_count = context.processed_items
            reason = f"Progress-based: {items_since_save} items processed"
        else:
            reason = ""

        return should_save, reason


class RateLimitAwareStrategy(SaveStrategy):
    """Save checkpoint when approaching rate limits."""

    def __init__(self, threshold_percentage: float = 0.2):
        """
        Initialize with threshold for remaining rate limit.

        Args:
            threshold_percentage: Save when remaining rate limit drops below this percentage
        """
        self.threshold = threshold_percentage

    def should_save(self, context: CheckpointContext) -> tuple[bool, str]:
        """Save if approaching rate limit threshold."""
        if context.rate_limit_remaining is None or context.rate_limit_total is None:
            return False, ""

        remaining_percentage = context.rate_limit_remaining / context.rate_limit_total
        should_save = remaining_percentage <= self.threshold

        if should_save:
            reason = (
                f"Rate-limit: {context.rate_limit_remaining}/{context.rate_limit_total} "
                f"({remaining_percentage:.1%} remaining <= {self.threshold:.1%} threshold)"
            )
        else:
            reason = ""

        return should_save, reason


class CompositeStrategy(SaveStrategy):
    """Combine multiple strategies with AND/OR logic."""

    def __init__(self, strategies: list[SaveStrategy], operator: str = "OR"):
        """
        Initialize with list of strategies.

        Args:
            strategies: List of save strategies to combine
            operator: "AND" or "OR" for combining strategies
        """
        self.strategies = strategies
        self.operator = operator.upper()
        if self.operator not in ("AND", "OR"):
            raise ValueError("Operator must be 'AND' or 'OR'")

    def should_save(self, context: CheckpointContext) -> tuple[bool, str]:
        """Check all strategies and combine results."""
        results = []
        reasons = []

        for strategy in self.strategies:
            should_save, reason = strategy.should_save(context)
            results.append(should_save)
            if reason:
                reasons.append(reason)

        if self.operator == "OR":
            final_result = any(results)
        else:
            final_result = all(results)

        final_reason = " | ".join(reasons) if final_result and reasons else ""
        return final_result, final_reason


class CheckpointManager:
    """Centralized checkpoint management for long-running operations."""

    def __init__(
        self,
        checkpoint_dir: Path | None = None,
        save_strategy: SaveStrategy | None = None,
        auto_cleanup: bool = True,
    ):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for checkpoint files (default: current directory)
            save_strategy: Strategy for determining when to save (default: time-based)
            auto_cleanup: Automatically delete checkpoint on successful completion
        """
        self.logger = get_logger(__name__)
        self.checkpoint_dir = checkpoint_dir or Path(".")
        self.save_strategy = save_strategy or TimeBasedStrategy(300)
        self.auto_cleanup = auto_cleanup
        self._start_time = time.time()
        self._last_save_time = 0
        self._save_count = 0

        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, operation_id: str) -> Path:
        """Get checkpoint file path for operation."""
        safe_id = operation_id.replace("/", "_").replace(" ", "_")
        return self.checkpoint_dir / f".checkpoint_{safe_id}.json"

    def create_checkpoint(
        self,
        operation_id: str,
        state: dict,
        metadata: dict | None = None,
        context: CheckpointContext | None = None,
    ) -> Path:
        """
        Create or update a checkpoint.

        Args:
            operation_id: Unique identifier for the operation
            state: Current state to save
            metadata: Optional metadata
            context: Optional context for save decision

        Returns:
            Path to checkpoint file
        """
        checkpoint_path = self._get_checkpoint_path(operation_id)

        # Load existing checkpoint to preserve creation time
        existing = self.load_checkpoint(operation_id)
        if existing:
            created_at = existing.created_at
            existing_metadata = asdict(existing.metadata)
        else:
            created_at = datetime.now().isoformat()
            existing_metadata = {}

        # Merge metadata
        checkpoint_metadata = CheckpointMetadata(**existing_metadata)
        if metadata:
            for key, value in metadata.items():
                if hasattr(checkpoint_metadata, key):
                    setattr(checkpoint_metadata, key, value)

        # Update save count and reason
        self._save_count += 1
        checkpoint_metadata.save_count = self._save_count

        if context:
            checkpoint_metadata.rate_limit_remaining = context.rate_limit_remaining
            checkpoint_metadata.rate_limit_total = context.rate_limit_total

        # Create checkpoint data
        checkpoint = CheckpointData(
            operation_id=operation_id,
            state=state,
            metadata=checkpoint_metadata,
            created_at=created_at,
            last_updated=datetime.now().isoformat(),
        )

        # Save to file
        try:
            with open(checkpoint_path, "w") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

            self._last_save_time = time.time() - self._start_time

            self.logger.info(
                "Checkpoint saved",
                operation_id=operation_id,
                path=str(checkpoint_path),
                save_count=self._save_count,
                reason=checkpoint_metadata.last_save_reason,
            )

            return checkpoint_path

        except Exception as e:
            self.logger.error(
                "Failed to save checkpoint",
                operation_id=operation_id,
                error=str(e),
            )
            raise

    def load_checkpoint(self, operation_id: str) -> CheckpointData | None:
        """
        Load existing checkpoint if available.

        Args:
            operation_id: Unique identifier for the operation

        Returns:
            CheckpointData if found, None otherwise
        """
        checkpoint_path = self._get_checkpoint_path(operation_id)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)

            checkpoint = CheckpointData.from_dict(data)

            self.logger.info(
                "Checkpoint loaded",
                operation_id=operation_id,
                version=checkpoint.version,
                processed_items=checkpoint.metadata.processed_items,
            )

            return checkpoint

        except Exception as e:
            self.logger.error(
                "Failed to load checkpoint",
                operation_id=operation_id,
                error=str(e),
            )
            return None

    def delete_checkpoint(self, operation_id: str) -> bool:
        """
        Delete checkpoint file.

        Args:
            operation_id: Unique identifier for the operation

        Returns:
            True if deleted, False if not found
        """
        checkpoint_path = self._get_checkpoint_path(operation_id)

        if not checkpoint_path.exists():
            return False

        try:
            checkpoint_path.unlink()
            self.logger.info(
                "Checkpoint deleted",
                operation_id=operation_id,
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to delete checkpoint",
                operation_id=operation_id,
                error=str(e),
            )
            return False

    def should_save(self, context: CheckpointContext) -> tuple[bool, str]:
        """
        Check if checkpoint should be saved based on strategy.

        Args:
            context: Current operation context

        Returns:
            Tuple of (should_save, reason)
        """
        # Update context with timing information
        context.elapsed_time = time.time() - self._start_time
        context.last_save_time = self._last_save_time

        return self.save_strategy.should_save(context)

    def finalize(self, operation_id: str) -> None:
        """
        Finalize checkpoint operation.

        Args:
            operation_id: Unique identifier for the operation
        """
        if self.auto_cleanup:
            self.delete_checkpoint(operation_id)
            self.logger.info(
                "Checkpoint finalized and cleaned up",
                operation_id=operation_id,
            )