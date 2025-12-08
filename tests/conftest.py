"""
Pytest configuration and shared fixtures.

This file contains pytest configuration and reusable test fixtures.
"""

import pytest
from pathlib import Path
from typing import Generator
import tempfile
import shutil

from src.bidsio.core.models import (
    BIDSDataset,
    BIDSSubject,
    BIDSSession,
    BIDSFile,
    BIDSDerivative,
    ExportRequest,
    SelectedEntities
)


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


@pytest.fixture
def sample_file() -> BIDSFile:
    """
    Create a sample BIDS file for testing.
    
    Returns:
        A BIDSFile with typical properties.
    """
    return BIDSFile(
        path=Path("/test/data/sub-01/ses-pre/anat/sub-01_ses-pre_T1w.nii.gz"),
        modality="anat",
        suffix="T1w",
        extension=".nii.gz",
        entities={"sub": "01", "ses": "pre"}
    )


@pytest.fixture
def sample_derivative() -> BIDSDerivative:
    """
    Create a sample derivative for testing.
    
    Returns:
        A BIDSDerivative with sessions and files.
    """
    file1 = BIDSFile(
        path=Path("/test/derivatives/pipeline1/sub-01/ses-pre/anat/sub-01_ses-pre_space-MNI_T1w.nii.gz"),
        modality="anat",
        suffix="T1w",
        extension=".nii.gz",
        entities={"sub": "01", "ses": "pre", "space": "MNI"}
    )
    
    session = BIDSSession(session_id="pre", files=[file1])
    
    return BIDSDerivative(
        pipeline_name="pipeline1",
        sessions=[session],
        files=[],
        pipeline_description={"Name": "Pipeline 1", "Version": "1.0"}
    )


@pytest.fixture
def sample_selected_entities() -> SelectedEntities:
    """
    Create sample SelectedEntities for testing.
    
    Returns:
        A SelectedEntities object with typical selections.
    """
    return SelectedEntities(
        entities={"sub": ["01", "02"], "ses": ["pre", "post"]},
        derivative_pipelines=["pipeline1"]
    )


@pytest.fixture
def sample_export_request(sample_dataset, sample_selected_entities, temp_dir) -> ExportRequest:
    """
    Create a sample ExportRequest for testing.
    
    Returns:
        An ExportRequest with test data.
    """
    return ExportRequest(
        source_dataset=sample_dataset,
        selected_entities=sample_selected_entities,
        output_path=temp_dir / "export"
    )
