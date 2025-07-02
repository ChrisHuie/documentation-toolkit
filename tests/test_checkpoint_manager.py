"""Tests for checkpoint manager."""

import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.shared_utilities.checkpoint_manager import (
    CheckpointContext,
    CheckpointData,
    CheckpointManager,
    CheckpointMetadata,
    CompositeStrategy,
    ProgressBasedStrategy,
    RateLimitAwareStrategy,
    TimeBasedStrategy,
)


class TestCheckpointManager:
    """Test checkpoint manager functionality."""

    def test_create_and_load_checkpoint(self):
        """Test creating and loading a checkpoint."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=Path(tmpdir))
            operation_id = "test_operation"
            state = {"files": ["file1.txt", "file2.txt"], "processed": 2}
            metadata = {"total_items": 10, "processed_items": 2}

            # Create checkpoint
            checkpoint_path = manager.create_checkpoint(
                operation_id, state, metadata
            )
            assert checkpoint_path.exists()

            # Load checkpoint
            loaded = manager.load_checkpoint(operation_id)
            assert loaded is not None
            assert loaded.operation_id == operation_id
            assert loaded.state == state
            assert loaded.metadata.total_items == 10
            assert loaded.metadata.processed_items == 2

    def test_checkpoint_not_found(self):
        """Test loading non-existent checkpoint."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=Path(tmpdir))
            loaded = manager.load_checkpoint("non_existent")
            assert loaded is None

    def test_delete_checkpoint(self):
        """Test deleting a checkpoint."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=Path(tmpdir))
            operation_id = "test_delete"

            # Create checkpoint
            manager.create_checkpoint(operation_id, {"test": "data"})

            # Delete checkpoint
            deleted = manager.delete_checkpoint(operation_id)
            assert deleted is True

            # Verify it's gone
            loaded = manager.load_checkpoint(operation_id)
            assert loaded is None

    def test_v1_checkpoint_migration(self):
        """Test migration from v1.0 checkpoint format."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=Path(tmpdir))
            operation_id = "test_migration"

            # Create v1.0 format checkpoint manually
            v1_data = {
                "files_data": {"file1.txt": "", "file2.txt": ""},
                "processed_files": ["file1.txt", "file2.txt"],
                "timestamp": time.time(),
                "completed": False,
            }

            checkpoint_path = manager._get_checkpoint_path(operation_id)
            with open(checkpoint_path, "w") as f:
                json.dump(v1_data, f)

            # Load and verify migration
            loaded = manager.load_checkpoint(operation_id)
            assert loaded is not None
            assert loaded.version == "2.0"
            assert loaded.state["files_data"] == v1_data["files_data"]
            assert loaded.state["processed_files"] == v1_data["processed_files"]

    def test_v1_array_format_migration(self):
        """Test migration from v1.0 array format."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=Path(tmpdir))
            operation_id = "test_array_migration"

            # Create v1.0 format with array files_data
            v1_data = {
                "files_data": [
                    {"path": "file1.txt", "sha": "abc123"},
                    {"path": "file2.txt", "sha": "def456"},
                ],
                "processed_files": ["file1.txt", "file2.txt"],
                "timestamp": time.time(),
            }

            checkpoint_path = manager._get_checkpoint_path(operation_id)
            with open(checkpoint_path, "w") as f:
                json.dump(v1_data, f)

            # Load and verify migration
            loaded = manager.load_checkpoint(operation_id)
            assert loaded is not None
            assert loaded.version == "2.0"
            assert isinstance(loaded.state["files_data"], dict)
            assert "file1.txt" in loaded.state["files_data"]
            assert "file2.txt" in loaded.state["files_data"]

    def test_auto_cleanup(self):
        """Test automatic cleanup on finalize."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(
                checkpoint_dir=Path(tmpdir), auto_cleanup=True
            )
            operation_id = "test_cleanup"

            # Create checkpoint
            manager.create_checkpoint(operation_id, {"test": "data"})

            # Finalize should delete it
            manager.finalize(operation_id)

            # Verify it's gone
            loaded = manager.load_checkpoint(operation_id)
            assert loaded is None

    def test_no_auto_cleanup(self):
        """Test disabling automatic cleanup."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(
                checkpoint_dir=Path(tmpdir), auto_cleanup=False
            )
            operation_id = "test_no_cleanup"

            # Create checkpoint
            manager.create_checkpoint(operation_id, {"test": "data"})

            # Finalize should not delete it
            manager.finalize(operation_id)

            # Verify it still exists
            loaded = manager.load_checkpoint(operation_id)
            assert loaded is not None


class TestSaveStrategies:
    """Test checkpoint save strategies."""

    def test_time_based_strategy(self):
        """Test time-based save strategy."""
        strategy = TimeBasedStrategy(interval_seconds=5)

        # Should not save initially
        context = CheckpointContext(elapsed_time=2, last_save_time=0)
        should_save, reason = strategy.should_save(context)
        assert should_save is False

        # Should save after interval
        context.elapsed_time = 6
        should_save, reason = strategy.should_save(context)
        assert should_save is True
        assert "Time-based" in reason

    def test_progress_based_strategy(self):
        """Test progress-based save strategy."""
        strategy = ProgressBasedStrategy(items_interval=100)

        # Should not save initially
        context = CheckpointContext(processed_items=50)
        should_save, reason = strategy.should_save(context)
        assert should_save is False

        # Should save after processing enough items
        context.processed_items = 100
        should_save, reason = strategy.should_save(context)
        assert should_save is True
        assert "Progress-based" in reason
        assert "100 items" in reason

        # Should not save again until next interval
        context.processed_items = 150
        should_save, reason = strategy.should_save(context)
        assert should_save is False

        # Should save at next interval
        context.processed_items = 200
        should_save, reason = strategy.should_save(context)
        assert should_save is True

    def test_rate_limit_aware_strategy(self):
        """Test rate limit aware save strategy."""
        strategy = RateLimitAwareStrategy(threshold_percentage=0.2)

        # Should not save when rate limit is high
        context = CheckpointContext(
            rate_limit_remaining=800, rate_limit_total=1000
        )
        should_save, reason = strategy.should_save(context)
        assert should_save is False

        # Should save when approaching limit
        context.rate_limit_remaining = 150
        should_save, reason = strategy.should_save(context)
        assert should_save is True
        assert "Rate-limit" in reason
        assert "15.0%" in reason

        # Should not save if rate limit info missing
        context.rate_limit_remaining = None
        should_save, reason = strategy.should_save(context)
        assert should_save is False

    def test_composite_strategy_or(self):
        """Test composite strategy with OR logic."""
        time_strategy = TimeBasedStrategy(interval_seconds=10)
        progress_strategy = ProgressBasedStrategy(items_interval=100)
        composite = CompositeStrategy([time_strategy, progress_strategy], "OR")

        # Neither condition met
        context = CheckpointContext(
            elapsed_time=5, last_save_time=0, processed_items=50
        )
        should_save, reason = composite.should_save(context)
        assert should_save is False

        # Time condition met
        context.elapsed_time = 11
        should_save, reason = composite.should_save(context)
        assert should_save is True
        assert "Time-based" in reason

        # Progress condition met
        context = CheckpointContext(
            elapsed_time=5, last_save_time=0, processed_items=100
        )
        should_save, reason = composite.should_save(context)
        assert should_save is True
        assert "Progress-based" in reason

    def test_composite_strategy_and(self):
        """Test composite strategy with AND logic."""
        time_strategy = TimeBasedStrategy(interval_seconds=10)
        progress_strategy = ProgressBasedStrategy(items_interval=100)
        composite = CompositeStrategy([time_strategy, progress_strategy], "AND")

        # Only one condition met
        context = CheckpointContext(
            elapsed_time=11, last_save_time=0, processed_items=50
        )
        should_save, reason = composite.should_save(context)
        assert should_save is False

        # Both conditions met
        context.processed_items = 100
        should_save, reason = composite.should_save(context)
        assert should_save is True
        assert "Time-based" in reason
        assert "Progress-based" in reason


class TestCheckpointIntegration:
    """Test checkpoint manager integration scenarios."""

    def test_checkpoint_with_all_strategies(self):
        """Test checkpoint manager with composite strategy."""
        with TemporaryDirectory() as tmpdir:
            # Create manager with all strategies
            composite_strategy = CompositeStrategy([
                TimeBasedStrategy(interval_seconds=5),
                ProgressBasedStrategy(items_interval=100),
                RateLimitAwareStrategy(threshold_percentage=0.2),
            ])

            manager = CheckpointManager(
                checkpoint_dir=Path(tmpdir),
                save_strategy=composite_strategy,
            )

            operation_id = "test_composite"

            # Initial save
            manager.create_checkpoint(
                operation_id,
                {"files": [], "count": 0},
                {"processed_items": 0},
            )

            # Test time-based trigger
            time.sleep(0.1)  # Small delay to ensure timing
            context = CheckpointContext(
                elapsed_time=6,
                last_save_time=0,
                processed_items=50,
                rate_limit_remaining=800,
                rate_limit_total=1000,
            )
            should_save, reason = manager.should_save(context)
            assert should_save is True
            assert "Time-based" in reason

            # Test progress-based trigger
            context = CheckpointContext(
                elapsed_time=2,
                last_save_time=0,
                processed_items=100,
                rate_limit_remaining=800,
                rate_limit_total=1000,
            )
            should_save, reason = manager.should_save(context)
            assert should_save is True
            assert "Progress-based" in reason

            # Test rate-limit trigger
            context = CheckpointContext(
                elapsed_time=2,
                last_save_time=0,
                processed_items=50,
                rate_limit_remaining=150,
                rate_limit_total=1000,
            )
            should_save, reason = manager.should_save(context)
            assert should_save is True
            assert "Rate-limit" in reason

    def test_checkpoint_metadata_updates(self):
        """Test checkpoint metadata is properly updated."""
        with TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=Path(tmpdir))
            operation_id = "test_metadata"

            # Create initial checkpoint
            manager.create_checkpoint(
                operation_id,
                {"files": ["file1.txt"]},
                {
                    "total_items": 100,
                    "processed_items": 1,
                    "tool_name": "test_tool",
                },
            )

            # Update checkpoint with new metadata
            context = CheckpointContext(
                processed_items=50,
                rate_limit_remaining=400,
                rate_limit_total=1000,
            )
            manager.create_checkpoint(
                operation_id,
                {"files": ["file1.txt", "file2.txt"]},
                {"processed_items": 50, "error_count": 2},
                context=context,
            )

            # Load and verify
            loaded = manager.load_checkpoint(operation_id)
            assert loaded.metadata.processed_items == 50
            assert loaded.metadata.error_count == 2
            assert loaded.metadata.tool_name == "test_tool"  # Preserved
            assert loaded.metadata.rate_limit_remaining == 400
            assert loaded.metadata.save_count == 2