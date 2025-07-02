# Checkpoint Manager

The Checkpoint Manager is a shared utility that provides resumable state management for long-running operations, particularly those involving GitHub API calls.

## Overview

The checkpoint system allows operations to:
- Save progress at strategic intervals
- Resume from the last saved state after interruption
- Avoid repeating expensive API calls
- Protect against rate limit exhaustion

## Usage

### Basic Example

```python
from src.shared_utilities.checkpoint_manager import CheckpointManager, TimeBasedStrategy

# Create a checkpoint manager
manager = CheckpointManager(
    checkpoint_dir=Path(".checkpoints"),
    save_strategy=TimeBasedStrategy(300),  # Save every 5 minutes
    auto_cleanup=True  # Delete checkpoint on success
)

# Save checkpoint
manager.create_checkpoint(
    operation_id="my_operation",
    state={"processed_items": processed_list},
    metadata={"total_items": 1000, "processed_items": len(processed_list)}
)

# Load checkpoint
checkpoint = manager.load_checkpoint("my_operation")
if checkpoint:
    processed_list = checkpoint.state["processed_items"]
```

### Save Strategies

#### Time-Based Strategy
Saves checkpoint after a specified time interval.

```python
strategy = TimeBasedStrategy(interval_seconds=300)  # Every 5 minutes
```

#### Progress-Based Strategy
Saves checkpoint after processing a certain number of items.

```python
strategy = ProgressBasedStrategy(items_interval=1000)  # Every 1000 items
```

#### Rate Limit Aware Strategy
Saves checkpoint when GitHub API rate limit falls below threshold.

```python
strategy = RateLimitAwareStrategy(threshold_percentage=0.2)  # Save at 20% remaining
```

#### Composite Strategy
Combines multiple strategies with AND/OR logic.

```python
strategy = CompositeStrategy([
    TimeBasedStrategy(300),
    ProgressBasedStrategy(1000),
    RateLimitAwareStrategy(0.2)
], operator="OR")  # Save if ANY condition is met
```

### Advanced Usage with Context

```python
from src.shared_utilities.checkpoint_manager import CheckpointContext

# Create context with current operation state
context = CheckpointContext(
    processed_items=750,
    total_items=1000,
    rate_limit_remaining=800,
    rate_limit_total=5000,
    elapsed_time=180.5
)

# Check if checkpoint should be saved
should_save, reason = manager.should_save(context)
if should_save:
    print(f"Saving checkpoint: {reason}")
    manager.create_checkpoint(...)
```

## Integration with GitHub Operations

The checkpoint manager is particularly useful for operations that make many GitHub API calls:

```python
def fetch_large_repository_data(repo_name: str):
    manager = CheckpointManager(
        save_strategy=CompositeStrategy([
            TimeBasedStrategy(300),
            RateLimitAwareStrategy(0.2)  # Critical for API operations
        ])
    )
    
    operation_id = f"fetch_{repo_name}".replace("/", "_")
    
    # Try to resume
    checkpoint = manager.load_checkpoint(operation_id)
    if checkpoint:
        processed_files = checkpoint.state.get("files", {})
    else:
        processed_files = {}
    
    # Process with periodic checkpoint saves
    for file in files_to_process:
        # ... process file ...
        
        context = CheckpointContext(
            processed_items=len(processed_files),
            rate_limit_remaining=get_rate_limit().remaining,
            rate_limit_total=get_rate_limit().limit
        )
        
        if manager.should_save(context)[0]:
            manager.create_checkpoint(
                operation_id,
                state={"files": processed_files}
            )
    
    # Cleanup on success
    manager.finalize(operation_id)
```

## Checkpoint Format

Checkpoints are stored as JSON files with the following structure:

```json
{
    "version": "2.0",
    "operation_id": "fetch_prebid_master_modules",
    "state": {
        "files_data": { ... },
        "processed_files": [ ... ]
    },
    "metadata": {
        "total_items": 1000,
        "processed_items": 750,
        "rate_limit_remaining": 800,
        "rate_limit_total": 5000,
        "save_count": 3,
        "last_save_reason": "Rate-limit: 800/5000 (16.0% remaining <= 20.0% threshold)"
    },
    "created_at": "2024-01-15T10:30:00",
    "last_updated": "2024-01-15T10:45:30"
}
```

## Configuration

### Environment Variables

- `CHECKPOINT_DIR` - Default directory for checkpoint files
- `CHECKPOINT_AUTO_CLEANUP` - Whether to delete checkpoints on success (default: true)

### Checkpoint File Location

By default, checkpoints are saved as hidden files in the current directory:
- Pattern: `.checkpoint_{operation_id}.json`
- Example: `.checkpoint_fetch_prebid_Prebid.js_master.json`

## Migration Support

The checkpoint manager automatically handles migration from v1.0 format (used by the legacy system) to v2.0 format. This includes:
- Converting array-based file data to dictionary format
- Preserving existing progress information
- Adding metadata structure

## Best Practices

1. **Choose appropriate save strategies** based on your operation:
   - Long-running: Use time-based strategy
   - API-heavy: Always include rate limit aware strategy
   - Large datasets: Use progress-based strategy

2. **Use meaningful operation IDs** that include:
   - Tool name
   - Repository or resource identifier
   - Version or timestamp

3. **Include relevant metadata** for debugging:
   - Total items to process
   - Error counts
   - Tool-specific information

4. **Handle checkpoint loading failures gracefully**:
   ```python
   checkpoint = manager.load_checkpoint(operation_id)
   if checkpoint and checkpoint.state:
       # Resume from checkpoint
       state = checkpoint.state
   else:
       # Start fresh
       state = {}
   ```

5. **Always call finalize()** on successful completion to clean up checkpoints