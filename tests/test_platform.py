#!/usr/bin/env python3
"""
HadesMP Platform Detection Tests — verifies platform detection logic.

These tests can run on any platform (Linux, WSL2, Windows).
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from hadesmp_platform import (
    detect_platform,
    detect_game_dir,
    GameConfig,
    _parse_libraryfolders_vdf,
)


class TestDetectPlatform(unittest.TestCase):
    """Test platform detection."""

    def test_returns_string(self):
        plat = detect_platform()
        self.assertIn(plat, ("windows", "wsl2", "linux"))

    def test_platform_matches_os(self):
        import platform as _platform
        plat = detect_platform()
        if _platform.system() == "Windows":
            self.assertEqual(plat, "windows")
        elif _platform.system() == "Linux":
            self.assertIn(plat, ("linux", "wsl2"))


class TestParseVdf(unittest.TestCase):
    """Test Steam libraryfolders.vdf parsing."""

    def test_parse_valid_vdf(self, tmp_path=None):
        """Parse a minimal libraryfolders.vdf."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".vdf", delete=False) as f:
            f.write('"libraryfolders"\n{\n')
            f.write('  "0"\n  {\n')
            f.write('    "path"\t\t"/tmp"\n')
            f.write('  }\n}\n')
            f.flush()
            paths = _parse_libraryfolders_vdf(Path(f.name))
        # /tmp should exist on Linux
        if Path("/tmp").is_dir():
            self.assertIn(Path("/tmp"), paths)
        os.unlink(f.name)

    def test_parse_missing_file(self):
        """Non-existent file should return empty list."""
        paths = _parse_libraryfolders_vdf(Path("/nonexistent/file.vdf"))
        self.assertEqual(paths, [])


class TestDetectGameDir(unittest.TestCase):
    """Test game directory detection."""

    def test_env_var_override(self):
        """HADES_ROOT env var should override auto-detection."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            hades_root = Path(tmpdir)
            x64_dir = hades_root / "x64"
            x64_dir.mkdir()
            content_dir = hades_root / "Content"
            content_dir.mkdir()

            with patch.dict(os.environ, {"HADES_ROOT": str(hades_root)}):
                config = detect_game_dir("windows")
                self.assertEqual(config.hades_root, hades_root)
                self.assertEqual(config.game_subdir, "x64")
                self.assertEqual(config.platform, "windows")
                self.assertFalse(config.is_wsl)

    def test_env_var_x64vk(self):
        """Should prefer x64Vk on Linux."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            hades_root = Path(tmpdir)
            (hades_root / "x64Vk").mkdir()
            (hades_root / "Content").mkdir()

            with patch.dict(os.environ, {"HADES_ROOT": str(hades_root)}):
                config = detect_game_dir("linux")
                self.assertEqual(config.game_subdir, "x64Vk")

    def test_missing_dir_raises(self):
        """Should raise FileNotFoundError when Hades is not found."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove HADES_ROOT if set
            os.environ.pop("HADES_ROOT", None)
            with self.assertRaises(FileNotFoundError):
                detect_game_dir("windows")


class TestGameConfig(unittest.TestCase):
    """Test GameConfig dataclass."""

    def test_paths(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "x64").mkdir()
            game_dir = root / "x64"
            config = GameConfig(
                game_dir=game_dir,
                hades_root=root,
                game_subdir="x64",
                platform="windows",
                is_wsl=False,
                log_path=game_dir / "hades_lua_stdout.log",
                inbox_path=game_dir / "hadesmp_inbox.lua",
                content_dir=root / "Content",
            )
            self.assertEqual(config.log_path, game_dir / "hades_lua_stdout.log")
            self.assertEqual(config.inbox_path, game_dir / "hadesmp_inbox.lua")


if __name__ == "__main__":
    unittest.main()
