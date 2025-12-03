"""
Pytest configuration and shared fixtures.

This file contains pytest configuration and reusable test fixtures.
"""

import pytest
from pathlib import Path
from typing import Generator
import tempfile
import shutil

from src.bidsio.core.models import BIDSDataset, BIDSSubject, BIDSSession


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test file operations.
    
    Yields:
        Path to temporary directory.
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_dataset() -> BIDSDataset:
    """
    Create a sample BIDS dataset for testing.
    
    Returns:
        A minimal BIDSDataset with a few subjects.
    """
    dataset = BIDSDataset(root_path=Path("/test/data"))
    
    # Add some subjects
    subject1 = BIDSSubject(subject_id="01")
    subject2 = BIDSSubject(subject_id="02")
    
    dataset.subjects = [subject1, subject2]
    
    return dataset


@pytest.fixture
def sample_subject() -> BIDSSubject:
    """
    Create a sample subject for testing.
    
    Returns:
        A BIDSSubject with sessions.
    """
    subject = BIDSSubject(subject_id="01")
    
    session1 = BIDSSession(session_id="01")
    session2 = BIDSSession(session_id="02")
    
    subject.sessions = [session1, session2]
    
    return subject


# TODO: add fixture for creating a mock BIDS directory structure on disk
# TODO: add fixture for sample FilterCriteria
# TODO: add fixture for sample ExportRequest
# TODO: add fixtures for GUI testing with pytest-qt
