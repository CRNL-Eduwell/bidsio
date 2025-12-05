"""  
Logging configuration for the application.

This module sets up centralized logging for all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .paths import get_log_file_path, get_old_log_file_path


def rotate_log_files() -> None:
    """
    Rotate log files before starting a new logging session.
    
    - If log.txt exists, move it to log.old.txt
    - If log.old.txt already exists, delete it first
    - This keeps only the last 2 instances of logging
    """
    log_file = get_log_file_path()
    old_log_file = get_old_log_file_path()
    
    if log_file.exists():
        # Remove old log file if it exists
        if old_log_file.exists():
            try:
                old_log_file.unlink()
            except Exception as e:
                # If we can't delete, just continue
                print(f"Warning: Could not delete old log file: {e}", file=sys.stderr)
        
        # Move current log to old log
        try:
            log_file.rename(old_log_file)
        except Exception as e:
            print(f"Warning: Could not rotate log file: {e}", file=sys.stderr)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
    log_to_file: bool = True
) -> None:
    """
    Configure application-wide logging.
    
    Logs are written to the persistent data directory by default.
    On each app startup, the previous log.txt is moved to log.old.txt.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        log_file: Optional path to a log file. If None and log_to_file=True, uses default location.
        format_string: Optional custom format string for log messages.
        log_to_file: Whether to log to a file. Default is True.
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)
    
    # File handler
    if log_to_file:
        # Use default log file location if not specified
        if log_file is None:
            log_file = get_log_file_path()
        
        # Rotate log files before starting new session
        rotate_log_files()
        
        # Ensure parent directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format=format_string,
        force=True  # Override any existing configuration
    )
    
    # Silence overly verbose third-party loggers
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
