"""
Command-line interface for BIDSIO.

This module provides a CLI for basic BIDS dataset operations.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..infrastructure.logging_config import setup_logging, get_logger
from ..infrastructure.bids_loader import is_bids_dataset, get_bids_version
from ..core.repository import BidsRepository
from ..core.models import FilterCriteria, ExportRequest


logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.
    
    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="bidsio",
        description="BIDS dataset explorer and export tool"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="BIDSIO 0.1.0"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Display dataset information")
    info_parser.add_argument("dataset", type=Path, help="Path to BIDS dataset")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate BIDS dataset")
    validate_parser.add_argument("dataset", type=Path, help="Path to BIDS dataset")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export dataset subset")
    export_parser.add_argument("dataset", type=Path, help="Path to BIDS dataset")
    export_parser.add_argument("output", type=Path, help="Output directory")
    export_parser.add_argument("--subjects", nargs="+", help="Subject IDs to include")
    export_parser.add_argument("--sessions", nargs="+", help="Session IDs to include")
    export_parser.add_argument("--tasks", nargs="+", help="Task names to include")
    export_parser.add_argument("--modalities", nargs="+", help="Modalities to include")
    export_parser.add_argument("--copy-mode", choices=["copy", "symlink", "hardlink"],
                              default="copy", help="File copy mode")
    
    # TODO: add more commands (list, filter, etc.)
    
    return parser


def cmd_info(args: argparse.Namespace) -> int:
    """
    Display information about a BIDS dataset.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code (0 for success).
    """
    dataset_path = args.dataset
    
    if not dataset_path.exists():
        logger.error(f"Dataset path does not exist: {dataset_path}")
        return 1
    
    if not is_bids_dataset(dataset_path):
        logger.error(f"Not a valid BIDS dataset: {dataset_path}")
        return 1
    
    print(f"Dataset: {dataset_path}")
    
    version = get_bids_version(dataset_path)
    if version:
        print(f"BIDS Version: {version}")
    
    # TODO: load dataset and display statistics
    # repository = BidsRepository(dataset_path)
    # dataset = repository.load()
    # print(f"Subjects: {len(dataset.subjects)}")
    # print(f"Modalities: {', '.join(dataset.get_all_modalities())}")
    # etc.
    
    print("TODO: Full dataset information not yet implemented")
    
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """
    Validate a BIDS dataset.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code (0 for valid dataset).
    """
    dataset_path = args.dataset
    
    if not dataset_path.exists():
        logger.error(f"Dataset path does not exist: {dataset_path}")
        return 1
    
    # TODO: implement proper BIDS validation
    # TODO: check for required files
    # TODO: validate filenames
    # TODO: check for consistency
    
    if is_bids_dataset(dataset_path):
        print(f"✓ Basic BIDS structure detected")
        print("TODO: Comprehensive validation not yet implemented")
        return 0
    else:
        print(f"✗ Not a valid BIDS dataset")
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """
    Export a filtered subset of a BIDS dataset.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code (0 for success).
    """
    dataset_path = args.dataset
    output_path = args.output
    
    if not dataset_path.exists():
        logger.error(f"Dataset path does not exist: {dataset_path}")
        return 1
    
    if not is_bids_dataset(dataset_path):
        logger.error(f"Not a valid BIDS dataset: {dataset_path}")
        return 1
    
    # TODO: load dataset
    # repository = BidsRepository(dataset_path)
    # dataset = repository.load()
    
    # TODO: create filter criteria from arguments
    # criteria = FilterCriteria(
    #     subject_ids=args.subjects,
    #     session_ids=args.sessions,
    #     task_names=args.tasks,
    #     modalities=args.modalities
    # )
    
    # TODO: create export request
    # request = ExportRequest(
    #     source_dataset=dataset,
    #     filter_criteria=criteria,
    #     output_path=output_path,
    #     copy_mode=args.copy_mode
    # )
    
    # TODO: perform export
    # from ..core.export import export_dataset
    # export_dataset(request)
    
    print("TODO: Export functionality not yet implemented")
    
    return 0


def main():
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Dispatch to command handler
    if args.command == "info":
        return cmd_info(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "export":
        return cmd_export(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
