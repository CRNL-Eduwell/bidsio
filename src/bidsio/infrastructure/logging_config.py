"""
Logging configuration for the application.

This module sets up centralized logging for all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        log_file: Optional path to a log file. If None, only console logging.
        format_string: Optional custom format string for log messages.
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # TODO: configure root logger
    # TODO: add console handler
    # TODO: add file handler if log_file is provided
    # TODO: set appropriate log levels for different modules
    # TODO: consider rotating file handler for production
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)
    
    # File handler
    if log_file is not None:
        # TODO: ensure parent directory exists
        # TODO: consider RotatingFileHandler or TimedRotatingFileHandler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format=format_string
    )
    
    # TODO: silence overly verbose third-party loggers if needed
    # logging.getLogger("some_library").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)


# TODO: add context manager for temporary log level changes
# TODO: add function to capture logs for testing
# TODO: consider structured logging (JSON) for production environments
