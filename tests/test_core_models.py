"""
Tests for core domain models.

These tests verify the behavior of data models in the core package.
"""

import pytest
from pathlib import Path

from src.bidsio.core.models import (
    BIDSFile,
    BIDSRun,
    BIDSSession,
    BIDSSubject,
    BIDSDataset,
    FilterCriteria,
    ExportRequest
)


class TestBIDSFile:
    """Tests for BIDSFile model."""
    
    def test_create_bids_file(self):
        """Test creating a BIDSFile instance."""
        file = BIDSFile(
            path=Path("/data/sub-01/anat/sub-01_T1w.nii.gz"),
            modality="anat",
            suffix="T1w",
            extension=".nii.gz"
        )
        
        assert file.path == Path("/data/sub-01/anat/sub-01_T1w.nii.gz")
        assert file.modality == "anat"
        assert file.suffix == "T1w"
    
    # TODO: test entity parsing from filename
    # TODO: test metadata loading from JSON sidecar


class TestBIDSSubject:
    """Tests for BIDSSubject model."""
    
    def test_create_subject(self):
        """Test creating a BIDSSubject instance."""
        subject = BIDSSubject(subject_id="01")
        assert subject.subject_id == "01"
        assert len(subject.sessions) == 0
        assert len(subject.files) == 0
    
    # TODO: test adding sessions to subject
    # TODO: test adding files to subject


class TestBIDSDataset:
    """Tests for BIDSDataset model."""
    
    def test_create_dataset(self):
        """Test creating a BIDSDataset instance."""
        dataset = BIDSDataset(root_path=Path("/data"))
        assert dataset.root_path == Path("/data")
        assert len(dataset.subjects) == 0
    
    def test_get_subject(self):
        """Test retrieving a subject by ID."""
        dataset = BIDSDataset(root_path=Path("/data"))
        subject1 = BIDSSubject(subject_id="01")
        subject2 = BIDSSubject(subject_id="02")
        dataset.subjects = [subject1, subject2]
        
        found = dataset.get_subject("01")
        assert found is not None
        assert found.subject_id == "01"
        
        not_found = dataset.get_subject("03")
        assert not_found is None
    
    # TODO: test get_all_modalities
    # TODO: test get_all_tasks


class TestFilterCriteria:
    """Tests for FilterCriteria model."""
    
    def test_create_empty_criteria(self):
        """Test creating empty filter criteria."""
        criteria = FilterCriteria()
        assert criteria.subject_ids is None
        assert criteria.session_ids is None
        assert criteria.task_names is None
    
    def test_create_with_subjects(self):
        """Test creating criteria with subject filter."""
        criteria = FilterCriteria(subject_ids=["01", "02"])
        assert criteria.subject_ids == ["01", "02"]
    
    # TODO: test validation of criteria


class TestExportRequest:
    """Tests for ExportRequest model."""
    
    def test_create_export_request(self):
        """Test creating an ExportRequest."""
        dataset = BIDSDataset(root_path=Path("/data"))
        criteria = FilterCriteria(subject_ids=["01"])
        
        request = ExportRequest(
            source_dataset=dataset,
            filter_criteria=criteria,
            output_path=Path("/output")
        )
        
        assert request.source_dataset == dataset
        assert request.filter_criteria == criteria
        assert request.output_path == Path("/output")
        assert request.copy_mode == "copy"
    
    # TODO: test validation of export request
