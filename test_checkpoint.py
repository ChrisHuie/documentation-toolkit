#!/usr/bin/env python3
"""
Simple test to verify checkpoint functionality works
"""

import json
import time
import os

def test_checkpoint():
    checkpoint_file = "test_checkpoint.json"
    
    # Simulate processing with checkpoints
    processed_items = []
    
    # Load from checkpoint if exists
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
            processed_items = data.get('processed_items', [])
            print(f"Loaded {len(processed_items)} items from checkpoint")
    
    # Simulate processing 100 items with checkpoints every 5 items
    total_items = 100
    last_checkpoint_time = time.time()
    
    for i in range(len(processed_items), total_items):
        processed_items.append(f"item_{i}")
        print(f"Processed item {i}")
        
        # Save checkpoint every 5 items or every 3 seconds
        current_time = time.time()
        if len(processed_items) % 5 == 0 or (current_time - last_checkpoint_time) >= 3:
            print(f"Saving checkpoint at item {i}")
            checkpoint_data = {
                'processed_items': processed_items,
                'timestamp': current_time,
                'completed': i == total_items - 1
            }
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f)
            last_checkpoint_time = current_time
        
        time.sleep(0.1)  # Simulate work
    
    # Clean up on completion
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("Cleaned up checkpoint file")
    
    print(f"Completed processing {len(processed_items)} items")

if __name__ == "__main__":
    test_checkpoint()