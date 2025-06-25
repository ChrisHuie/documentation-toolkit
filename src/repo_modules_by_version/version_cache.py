"""
Version cache system for storing repository version information
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class MajorVersionInfo:
    """Information about a major version."""

    major: int
    first_version: str  # e.g., "6.0.0"
    last_version: str  # e.g., "6.29.3"


@dataclass
class RepoVersionCache:
    """Cached version information for a repository."""

    repo_name: str
    default_branch: str
    major_versions: dict[int, MajorVersionInfo]
    latest_versions: list[str]  # 5 most recent versions


class VersionCacheManager:
    """Manages version caching for repositories."""

    def __init__(self, cache_dir: str | None = None):
        """Initialize cache manager."""
        if cache_dir is None:
            # Store cache in the repository's cache directory
            repo_root = Path(__file__).parent.parent.parent  # Go up to repo root
            self.cache_dir = repo_root / "cache" / "versions"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file(self, repo_name: str) -> Path:
        """Get cache file path for a repository."""
        # Replace / with _ for filename
        safe_name = repo_name.replace("/", "_")
        return self.cache_dir / f"{safe_name}.json"

    def load_cache(self, repo_name: str) -> RepoVersionCache | None:
        """Load cached version info for a repository."""
        cache_file = self._get_cache_file(repo_name)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            # Convert major_versions dict back to proper format
            major_versions = {}
            for major_str, info in data["major_versions"].items():
                major_versions[int(major_str)] = MajorVersionInfo(**info)

            return RepoVersionCache(
                repo_name=data["repo_name"],
                default_branch=data["default_branch"],
                major_versions=major_versions,
                latest_versions=data["latest_versions"],
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            # Invalid cache file, return None
            return None

    def save_cache(self, cache: RepoVersionCache) -> None:
        """Save version cache for a repository."""
        cache_file = self._get_cache_file(cache.repo_name)

        # Convert to dict for JSON serialization
        data = asdict(cache)

        # Convert major version keys to strings for JSON
        major_versions_str = {}
        for major, info in data["major_versions"].items():
            major_versions_str[str(major)] = info
        data["major_versions"] = major_versions_str

        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)

    def needs_update(self, cache: RepoVersionCache, current_latest_major: int) -> bool:
        """Check if cache needs updating based on current latest major version."""
        if not cache.major_versions:
            return True

        cached_latest_major = max(cache.major_versions.keys())
        return current_latest_major > cached_latest_major

    def clear_cache(self, repo_name: str | None = None) -> None:
        """Clear cache for a specific repo or all repos."""
        if repo_name:
            cache_file = self._get_cache_file(repo_name)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
