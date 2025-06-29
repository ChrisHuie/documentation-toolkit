"""
Tests for output directory management utilities.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from src.shared_utilities.output_manager import (
    OutputManager,
    cleanup_empty_directories,
    get_output_path,
    save_output,
)


class TestOutputManager:
    """Test cases for OutputManager class."""

    def test_init_default_base_dir(self):
        """Test initialization with default base directory."""
        manager = OutputManager()
        assert manager.base_dir == Path("output")

    def test_init_custom_base_dir(self):
        """Test initialization with custom base directory."""
        manager = OutputManager("custom_output")
        assert manager.base_dir == Path("custom_output")

    def test_get_output_path_creates_directories(self):
        """Test that get_output_path creates directories when requested."""
        manager = OutputManager()

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            path = manager.get_output_path(
                tool_name="test-tool",
                repo_name="owner/repo",
                version="v1.0.0",
                filename="test.txt",
                create_dirs=True,
            )

            # Verify path structure
            assert path == Path("output/test-tool/repo/1.0.0/test.txt")

            # Verify mkdir was called
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_get_output_path_no_create_directories(self):
        """Test that get_output_path doesn't create directories when not requested."""
        manager = OutputManager()

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            path = manager.get_output_path(
                tool_name="test-tool",
                repo_name="owner/repo",
                version="v1.0.0",
                filename="test.txt",
                create_dirs=False,
            )

            # Verify path structure
            assert path == Path("output/test-tool/repo/1.0.0/test.txt")

            # Verify mkdir was not called
            mock_mkdir.assert_not_called()

    def test_get_output_path_cleans_repo_name(self):
        """Test that repo names are cleaned properly."""
        manager = OutputManager()

        # Test with owner/repo format
        path1 = manager.get_output_path(
            tool_name="tool",
            repo_name="prebid/Prebid.js",
            version="v1.0.0",
            filename="file.txt",
            create_dirs=False,
        )
        assert path1 == Path("output/tool/Prebid.js/1.0.0/file.txt")

        # Test with just repo name
        path2 = manager.get_output_path(
            tool_name="tool",
            repo_name="Prebid.js",
            version="v1.0.0",
            filename="file.txt",
            create_dirs=False,
        )
        assert path2 == Path("output/tool/Prebid.js/1.0.0/file.txt")

    def test_get_output_path_cleans_version(self):
        """Test that version strings are cleaned properly."""
        manager = OutputManager()

        # Test with v prefix
        path1 = manager.get_output_path(
            tool_name="tool",
            repo_name="repo",
            version="v1.0.0",
            filename="file.txt",
            create_dirs=False,
        )
        assert path1 == Path("output/tool/repo/1.0.0/file.txt")

        # Test without v prefix
        path2 = manager.get_output_path(
            tool_name="tool",
            repo_name="repo",
            version="1.0.0",
            filename="file.txt",
            create_dirs=False,
        )
        assert path2 == Path("output/tool/repo/1.0.0/file.txt")

    def test_save_output(self):
        """Test saving output content."""
        manager = OutputManager()
        content = "Test content"

        with (
            patch("pathlib.Path.write_text") as mock_write,
            patch("pathlib.Path.mkdir"),
        ):
            path = manager.save_output(
                content=content,
                tool_name="test-tool",
                repo_name="repo",
                version="v1.0.0",
                filename="test.txt",
            )

            # Verify content was written
            mock_write.assert_called_once_with(content)

            # Verify correct path
            assert path == Path("output/test-tool/repo/1.0.0/test.txt")

    def test_cleanup_empty_directories_specific_tool(self):
        """Test cleanup of empty directories for a specific tool."""
        manager = OutputManager()

        # Mock os.walk to return some empty directories
        walk_data = [
            ("output/test-tool/repo/1.0.0", [], []),  # Empty dir
            ("output/test-tool/repo", ["1.0.0"], []),  # Not empty
            ("output/test-tool", ["repo"], []),  # Not empty
        ]

        with (
            patch("os.walk", return_value=walk_data),
            patch("pathlib.Path.rmdir") as mock_rmdir,
            patch("pathlib.Path.exists", return_value=True),
        ):
            count = manager.cleanup_empty_directories("test-tool")

            # Should remove only the empty version directory
            assert count == 1
            mock_rmdir.assert_called_once()

    def test_cleanup_empty_directories_all_tools(self):
        """Test cleanup of empty directories for all tools."""
        manager = OutputManager()

        # Mock os.walk to return multiple empty directories
        walk_data = [
            ("output/tool1/repo/1.0.0", [], []),  # Empty
            ("output/tool1/repo/2.0.0", [], []),  # Empty
            ("output/tool2/repo/1.0.0", [], []),  # Empty
        ]

        with (
            patch("os.walk", return_value=walk_data),
            patch("pathlib.Path.rmdir") as mock_rmdir,
            patch("pathlib.Path.exists", return_value=True),
        ):
            count = manager.cleanup_empty_directories()

            # Should remove all 3 empty directories
            assert count == 3
            assert mock_rmdir.call_count == 3

    def test_cleanup_empty_directories_skip_base(self):
        """Test that cleanup doesn't remove the base output directory."""
        manager = OutputManager()

        # Mock os.walk to return only the base directory as empty
        walk_data = [
            ("output", [], []),  # Base dir, should not be removed
        ]

        with (
            patch("os.walk", return_value=walk_data),
            patch("pathlib.Path.rmdir") as mock_rmdir,
            patch("pathlib.Path.exists", return_value=True),
        ):
            count = manager.cleanup_empty_directories()

            # Should not remove any directories
            assert count == 0
            mock_rmdir.assert_not_called()

    def test_cleanup_empty_directories_handles_errors(self):
        """Test that cleanup handles OSError gracefully."""
        manager = OutputManager()

        walk_data = [
            ("output/test-tool/repo/1.0.0", [], []),  # Empty dir
        ]

        with (
            patch("os.walk", return_value=walk_data),
            patch("pathlib.Path.rmdir", side_effect=OSError("Permission denied")),
            patch("pathlib.Path.exists", return_value=True),
        ):
            # Should not raise exception
            count = manager.cleanup_empty_directories()
            assert count == 0

    def test_get_existing_outputs_specific_version(self):
        """Test getting existing outputs for a specific version."""
        manager = OutputManager()

        # Mock file structure
        mock_files = [
            Path("output/tool/repo/1.0.0/file1.txt"),
            Path("output/tool/repo/1.0.0/file2.txt"),
        ]

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.glob", return_value=mock_files),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            outputs = manager.get_existing_outputs(
                tool_name="tool", repo_name="repo", version="v1.0.0"
            )

            assert len(outputs) == 2
            assert all(isinstance(p, Path) for p in outputs)

    def test_get_existing_outputs_all_versions(self):
        """Test getting existing outputs for all versions of a repo."""
        manager = OutputManager()

        # Mock file paths that will be returned
        mock_files = [
            Path("output/tool/repo/1.0.0/file1.txt"),
            Path("output/tool/repo/2.0.0/file2.txt"),
        ]

        # Mock the path structure and operations
        with patch.object(manager, "base_dir") as mock_base_dir:
            # Create a mock that handles the path operations
            mock_tool_path = Mock()
            mock_tool_path.exists.return_value = True

            mock_repo_path = Mock()
            mock_repo_path.exists.return_value = True

            # Mock version directories
            mock_version_dir1 = Mock()
            mock_version_dir1.is_dir.return_value = True
            mock_version_dir1.glob.return_value = [mock_files[0]]

            mock_version_dir2 = Mock()
            mock_version_dir2.is_dir.return_value = True
            mock_version_dir2.glob.return_value = [mock_files[1]]

            mock_repo_path.iterdir.return_value = [mock_version_dir1, mock_version_dir2]
            mock_tool_path.__truediv__ = Mock(return_value=mock_repo_path)
            mock_base_dir.__truediv__ = Mock(return_value=mock_tool_path)

            with patch("pathlib.Path.is_file", return_value=True):
                outputs = manager.get_existing_outputs(
                    tool_name="tool", repo_name="repo"
                )

            assert len(outputs) == 2
            assert all(isinstance(p, Path) for p in outputs)

    def test_get_existing_outputs_nonexistent_tool(self):
        """Test getting outputs for a nonexistent tool."""
        manager = OutputManager()

        with patch("pathlib.Path.exists", return_value=False):
            outputs = manager.get_existing_outputs("nonexistent-tool")
            assert outputs == []

    def test_get_output_structure(self):
        """Test getting the output directory structure."""
        manager = OutputManager()

        # Create mock directory structure
        mock_base = Mock()
        mock_tool_dir = Mock()
        mock_tool_dir.name = "test-tool"
        mock_tool_dir.is_dir.return_value = True

        mock_repo_dir = Mock()
        mock_repo_dir.name = "repo"
        mock_repo_dir.is_dir.return_value = True

        mock_version_dir = Mock()
        mock_version_dir.name = "1.0.0"
        mock_version_dir.is_dir.return_value = True

        mock_file = Mock()
        mock_file.name = "test.txt"
        mock_file.is_file.return_value = True

        mock_version_dir.glob.return_value = [mock_file]
        mock_repo_dir.iterdir.return_value = [mock_version_dir]
        mock_tool_dir.iterdir.return_value = [mock_repo_dir]
        mock_base.iterdir.return_value = [mock_tool_dir]

        with patch.object(manager, "base_dir", mock_base):
            structure = manager.get_output_structure()

            expected = {"test-tool": {"repo": {"1.0.0": ["test.txt"]}}}
            assert structure == expected

    def test_get_output_structure_specific_tool(self):
        """Test getting output structure for a specific tool."""
        manager = OutputManager()

        mock_tool_path = Mock()
        mock_tool_path.exists.return_value = True
        mock_tool_path.name = "test-tool"
        mock_tool_path.iterdir.return_value = []

        with patch.object(Path, "__truediv__", return_value=mock_tool_path):
            structure = manager.get_output_structure("test-tool")
            assert structure == {"test-tool": {}}


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_output_path_convenience(self):
        """Test the convenience get_output_path function."""
        with patch(
            "src.shared_utilities.output_manager.get_default_output_manager"
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            get_output_path("tool", "repo", "v1.0.0", "file.txt")

            mock_manager.get_output_path.assert_called_once_with(
                "tool", "repo", "v1.0.0", "file.txt", True
            )

    def test_save_output_convenience(self):
        """Test the convenience save_output function."""
        with patch(
            "src.shared_utilities.output_manager.get_default_output_manager"
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            save_output("content", "tool", "repo", "v1.0.0", "file.txt")

            mock_manager.save_output.assert_called_once_with(
                "content", "tool", "repo", "v1.0.0", "file.txt"
            )

    def test_cleanup_empty_directories_convenience(self):
        """Test the convenience cleanup_empty_directories function."""
        with patch(
            "src.shared_utilities.output_manager.get_default_output_manager"
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            cleanup_empty_directories("tool")

            mock_manager.cleanup_empty_directories.assert_called_once_with("tool")

    def test_default_manager_singleton(self):
        """Test that get_default_output_manager returns a singleton."""
        # Reset the singleton
        import src.shared_utilities.output_manager
        from src.shared_utilities.output_manager import (
            get_default_output_manager,
        )

        src.shared_utilities.output_manager._default_manager = None

        manager1 = get_default_output_manager()
        manager2 = get_default_output_manager()

        assert manager1 is manager2
