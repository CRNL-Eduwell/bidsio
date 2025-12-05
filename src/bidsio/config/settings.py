"""
Application settings and configuration.

This module provides centralized access to application settings with automatic
persistence to disk. Settings are stored as JSON in a platform-specific location:

- Windows: %APPDATA%/LocalLow/bidsio/settings.json
- macOS: ~/Library/Application Support/bidsio/settings.json
- Linux: ~/.config/bidsio/settings.json

Settings are automatically loaded on first access and saved when updated.

Example:
    from bidsio.config.settings import get_settings, get_settings_manager
    
    # Get current settings
    settings = get_settings()
    print(settings.theme)
    
    # Update settings (auto-saves)
    manager = get_settings_manager()
    manager.update(theme="light_blue", window_width=1400)
    
    # Add recent dataset (auto-saves)
    manager.add_recent_dataset("/path/to/dataset")
"""

import json
import platform
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
import logging


@dataclass
class AppSettings:
    """Application-wide settings."""
    
    # Logging settings
    log_level: int = logging.INFO
    log_to_file: bool = False
    log_file_path: Optional[Path] = None
    
    # UI settings
    window_width: int = 1200
    window_height: int = 800
    theme: str = "dark_blue"  # Available: dark_blue, dark_teal, dark_amber, light_blue, light_teal, light_amber
    
    # BIDS settings
    validate_bids_on_load: bool = True
    cache_dataset_index: bool = True
    cache_directory: Optional[Path] = None
    lazy_loading: bool = False  # False = eager loading (default), True = lazy loading
    
    # Export settings
    default_copy_mode: str = "copy"  # 'copy', 'symlink', or 'hardlink'
    verify_exports: bool = True
    
    # Performance settings
    max_threads: int = 4
    enable_progress_callbacks: bool = True
    
    # Recent files
    recent_datasets: list[str] = field(default_factory=list)
    max_recent_items: int = 10
    
    # TODO: add settings for filter defaults
    # TODO: add settings for export templates


def get_persistent_data_directory() -> Path:
    """
    Get the persistent data directory for the application (cross-platform).
    
    Similar to Unity's persistentDataPath, this provides a location where
    application data can be saved persistently across sessions.
    
    Returns:
        Path to the persistent data directory.
        
    Platform-specific locations:
        - Windows: %APPDATA%/LocalLow/bidsio
        - macOS: ~/Library/Application Support/bidsio
        - Linux: ~/.config/bidsio
    """
    system = platform.system()
    app_name = "bidsio"
    
    if system == "Windows":
        # Windows: %APPDATA%/LocalLow/bidsio
        base = Path.home() / "AppData" / "LocalLow"
    elif system == "Darwin":
        # macOS: ~/Library/Application Support/bidsio
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux/Unix: ~/.config/bidsio
        base = Path.home() / ".config"
    
    data_dir = base / app_name
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir


class SettingsManager:
    """
    Manages loading and saving application settings.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the settings manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        if config_file is None:
            data_dir = get_persistent_data_directory()
            config_file = data_dir / "settings.json"
        
        self.config_file = config_file
        self._settings = AppSettings()
        self._logger = logging.getLogger(__name__)
    
    def load(self) -> AppSettings:
        """
        Load settings from configuration file.
        
        Returns:
            The loaded settings object.
        """
        if not self.config_file.exists():
            self._logger.info(f"Settings file not found at {self.config_file}, using defaults")
            return self._settings
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert Path strings back to Path objects
            if data.get('log_file_path'):
                data['log_file_path'] = Path(data['log_file_path'])
            if data.get('cache_directory'):
                data['cache_directory'] = Path(data['cache_directory'])
            
            # Update settings with loaded data
            for key, value in data.items():
                if hasattr(self._settings, key):
                    setattr(self._settings, key, value)
            
            self._logger.info(f"Settings loaded from {self.config_file}")
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse settings file: {e}. Using defaults.")
        except Exception as e:
            self._logger.error(f"Failed to load settings: {e}. Using defaults.")
        
        return self._settings
    
    def save(self, settings: Optional[AppSettings] = None) -> None:
        """
        Save settings to configuration file.
        
        Args:
            settings: Settings object to save. If None, saves current settings.
        """
        if settings is not None:
            self._settings = settings
        
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert dataclass to dict
            data = asdict(self._settings)
            
            # Convert Path objects to strings for JSON serialization
            if data.get('log_file_path'):
                data['log_file_path'] = str(data['log_file_path'])
            if data.get('cache_directory'):
                data['cache_directory'] = str(data['cache_directory'])
            
            # Atomic write: write to temp file, then rename
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Replace old file with new file atomically
            temp_file.replace(self.config_file)
            
            self._logger.info(f"Settings saved to {self.config_file}")
            
        except Exception as e:
            self._logger.error(f"Failed to save settings: {e}")
    
    def get(self) -> AppSettings:
        """
        Get the current settings.
        
        Returns:
            The current settings object.
        """
        return self._settings
    
    def update(self, **kwargs) -> None:
        """
        Update specific settings and auto-save.
        
        Args:
            **kwargs: Setting names and values to update.
        """
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
            else:
                self._logger.warning(f"Ignoring unknown setting: {key}")
        
        # Auto-save after update
        self.save()
    
    def add_recent_dataset(self, path: str) -> None:
        """
        Add a dataset path to the recent datasets list.
        
        Args:
            path: Path to the dataset to add.
        """
        # Remove if already in list
        if path in self._settings.recent_datasets:
            self._settings.recent_datasets.remove(path)
        
        # Add to front of list
        self._settings.recent_datasets.insert(0, path)
        
        # Trim to max_recent_items
        if len(self._settings.recent_datasets) > self._settings.max_recent_items:
            self._settings.recent_datasets = self._settings.recent_datasets[:self._settings.max_recent_items]
        
        # Auto-save
        self.save()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values and save."""
        self._settings = AppSettings()
        self.save()


# Global settings instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """
    Get the global settings manager instance.
    
    Returns:
        The global SettingsManager.
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        _settings_manager.load()
    return _settings_manager


def get_settings() -> AppSettings:
    """
    Get the current application settings.
    
    Returns:
        The current AppSettings object.
    """
    return get_settings_manager().get()


# TODO: add validators for settings values
# TODO: add migration logic for settings file format changes
# TODO: consider using environment variables for some settings


def get_settings_file_path() -> Path:
    """
    Get the path to the settings file.
    
    Returns:
        Path to the settings.json file.
    """
    return get_persistent_data_directory() / "settings.json"
