"""
Data models for module history tracking.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ModuleHistoryEntry:
    """Information about when a module was first introduced."""

    module_name: str
    module_type: str  # bid_adapter, analytics_adapter, etc.
    first_version: str  # e.g., "2.15.0"
    first_major_version: int  # e.g., 2
    file_path: str  # e.g., "modules/exampleBidAdapter.js"
    first_commit_date: str | None = None
    first_commit_sha: str | None = None


@dataclass
class ModuleHistoryResult:
    """Complete result from module history analysis."""

    repo_name: str
    total_modules: int
    modules_by_type: dict[str, list[ModuleHistoryEntry]]
    modules_by_version: dict[int, list[ModuleHistoryEntry]]
    metadata: dict[str, Any]


@dataclass
class HistoryCache:
    """Cache structure for module history data."""

    repo_name: str
    last_analyzed_version: str
    modules: dict[str, ModuleHistoryEntry]  # module_name -> entry
    metadata: dict[str, Any]
