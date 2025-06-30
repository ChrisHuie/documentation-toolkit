"""Module comparison tool for analyzing differences between versions and repositories."""

from .comparator import ModuleComparator
from .data_models import ComparisonResult, ModuleDifference

__all__ = ["ModuleComparator", "ComparisonResult", "ModuleDifference"]
