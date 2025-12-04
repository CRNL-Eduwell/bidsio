"""
Test script to demonstrate settings save/load functionality.

This script shows how settings are persisted to disk and loaded back.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from bidsio.config.settings import (
    get_settings_manager,
    get_settings_file_path,
    get_persistent_data_directory,
)


def main():
    """Test settings persistence."""
    print("=" * 60)
    print("Testing bidsio Settings Persistence")
    print("=" * 60)
    
    # Show where settings are stored
    data_dir = get_persistent_data_directory()
    settings_file = get_settings_file_path()
    
    print(f"\nPersistent data directory: {data_dir}")
    print(f"Settings file: {settings_file}")
    print(f"Settings file exists: {settings_file.exists()}")
    
    # Get settings manager
    manager = get_settings_manager()
    settings = manager.get()
    
    print("\n" + "=" * 60)
    print("Current Settings")
    print("=" * 60)
    print(f"Theme: {settings.theme}")
    print(f"Window size: {settings.window_width}x{settings.window_height}")
    print(f"Log level: {settings.log_level}")
    print(f"Recent datasets: {settings.recent_datasets}")
    
    # Update some settings
    print("\n" + "=" * 60)
    print("Updating Settings")
    print("=" * 60)
    print("Setting theme to 'light_blue'")
    print("Adding recent dataset '/path/to/dataset1'")
    
    manager.update(theme="light_blue", window_width=1400, window_height=900)
    manager.add_recent_dataset("/path/to/dataset1")
    manager.add_recent_dataset("/path/to/dataset2")
    
    print(f"\nSettings saved to: {settings_file}")
    
    # Load settings again to verify persistence
    print("\n" + "=" * 60)
    print("Creating new manager to verify persistence")
    print("=" * 60)
    
    from bidsio.config.settings import SettingsManager
    new_manager = SettingsManager()
    new_manager.load()
    new_settings = new_manager.get()
    
    print(f"Theme: {new_settings.theme}")
    print(f"Window size: {new_settings.window_width}x{new_settings.window_height}")
    print(f"Recent datasets: {new_settings.recent_datasets}")
    
    print("\n" + "=" * 60)
    print("Settings File Content")
    print("=" * 60)
    
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            print(f.read())
    
    print("\n✓ Settings persistence test completed successfully!")


if __name__ == "__main__":
    main()
