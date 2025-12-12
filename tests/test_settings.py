"""
Tests for the SettingsManager persistence behaviour.

These tests verify that settings are saved and loaded correctly and that the
global settings manager uses the persistent data directory when no custom
config_file is provided.
"""
from __future__ import annotations

from pathlib import Path
import importlib
import json

import pytest


def test_save_and_load(tmp_path: Path):
    from src.bidsio.config.settings import SettingsManager

    config_file = tmp_path / "settings.json"

    # Create a manager with a custom file path
    manager = SettingsManager(config_file=config_file)
    manager.load()

    # Update and add recent datasets (auto-saves)
    manager.update(theme="light_blue", window_width=1400, window_height=900)
    manager.add_recent_dataset("/path/to/dataset1")
    manager.add_recent_dataset("/path/to/dataset2")

    # File should be created
    assert config_file.exists()

    # Load again using a new manager instance to verify persistence
    new_manager = SettingsManager(config_file=config_file)
    new_manager.load()
    settings = new_manager.get()

    assert settings.theme == "light_blue"
    assert settings.window_width == 1400
    assert settings.window_height == 900
    assert "/path/to/dataset1" in settings.recent_datasets

    # Check contents on disk match expectations
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["theme"] == "light_blue"
    assert data["window_width"] == 1400
    assert data["window_height"] == 900


def test_get_settings_manager_uses_default_path(tmp_path: Path, monkeypatch):
    import src.bidsio.config.settings as settings_mod

    # Monkeypatch the persistent directory to the temporary path
    monkeypatch.setattr(
        "src.bidsio.config.settings.get_persistent_data_directory",
        lambda: tmp_path,
    )

    # Ensure we start with a fresh global manager
    settings_mod._settings_manager = None

    # Call the helper which should create a manager and write to our tmp path
    manager = settings_mod.get_settings_manager()
    assert manager.config_file.parent == tmp_path
    assert manager.config_file.name == "settings.json"
    assert manager.config_file.exists()

    # Cleanup the global manager for subsequent tests
    settings_mod._settings_manager = None
