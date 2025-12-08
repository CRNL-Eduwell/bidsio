"""
Tests for derivatives functionality.

Tests derivative scanning, loading, and integration with the data model.
"""

import pytest
import json
from pathlib import Path

from src.bidsio.core.models import (
    BIDSDataset,
    BIDSSubject,
    BIDSDerivative,
    BIDSSession,
    BIDSFile
)
from src.bidsio.infrastructure.bids_loader import BidsLoader


@pytest.fixture
def mock_derivatives_dataset(tmp_path):
    """
    Create a mock BIDS dataset with derivatives on disk.
    
    Structure:
        dataset/
            dataset_description.json
            participants.tsv
            sub-01/
                ses-pre/
                    anat/
                        sub-01_ses-pre_T1w.nii.gz
            sub-02/
                ses-post/
                    anat/
                        sub-02_ses-post_T1w.nii.gz
            derivatives/
                pipeline1/
                    dataset_description.json
                    sub-01/
                        ses-pre/
                            anat/
                                sub-01_ses-pre_space-MNI_T1w.nii.gz
                    sub-02/
                        ses-post/
                            anat/
                                sub-02_ses-post_space-MNI_T1w.nii.gz
                pipeline2/
                    dataset_description.json
                    analysis/
                        sub-01/
                            ses-pre/
                                anat/
                                    sub-01_ses-pre_desc-preproc_T1w.nii.gz
    """
    dataset_root = tmp_path / "derivatives_dataset"
    dataset_root.mkdir()
    
    # Dataset description
    desc = {
        "Name": "Derivatives Test Dataset",
        "BIDSVersion": "1.8.0",
        "Authors": ["Test Author"]
    }
    with open(dataset_root / "dataset_description.json", "w") as f:
        json.dump(desc, f)
    
    # Participants
    with open(dataset_root / "participants.tsv", "w") as f:
        f.write("participant_id\tage\n")
        f.write("sub-01\t25\n")
        f.write("sub-02\t30\n")
    
    # Raw data
    for sub_id, ses_id in [("01", "pre"), ("02", "post")]:
        anat_dir = dataset_root / f"sub-{sub_id}" / f"ses-{ses_id}" / "anat"
        anat_dir.mkdir(parents=True)
        (anat_dir / f"sub-{sub_id}_ses-{ses_id}_T1w.nii.gz").write_text("raw data")
    
    # Derivatives
    deriv_root = dataset_root / "derivatives"
    
    # Pipeline 1: Simple structure
    pipeline1_dir = deriv_root / "pipeline1"
    pipeline1_dir.mkdir(parents=True)
    
    pipeline1_desc = {
        "Name": "Pipeline 1",
        "BIDSVersion": "1.8.0",
        "PipelineDescription": {"Name": "Normalization Pipeline"},
        "GeneratedBy": [{"Name": "SPM", "Version": "12"}]
    }
    with open(pipeline1_dir / "dataset_description.json", "w") as f:
        json.dump(pipeline1_desc, f)
    
    for sub_id, ses_id in [("01", "pre"), ("02", "post")]:
        anat_dir = pipeline1_dir / f"sub-{sub_id}" / f"ses-{ses_id}" / "anat"
        anat_dir.mkdir(parents=True)
        (anat_dir / f"sub-{sub_id}_ses-{ses_id}_space-MNI_T1w.nii.gz").write_text("normalized")
        (anat_dir / f"sub-{sub_id}_ses-{ses_id}_space-MNI_T1w.json").write_text('{"space": "MNI"}')
    
    # Pipeline 2: Nested structure (analysis subfolder)
    pipeline2_dir = deriv_root / "pipeline2"
    pipeline2_dir.mkdir(parents=True)
    
    pipeline2_desc = {
        "Name": "Pipeline 2",
        "BIDSVersion": "1.8.0",
        "PipelineDescription": {"Name": "Preprocessing Pipeline"},
        "GeneratedBy": [{"Name": "fMRIPrep", "Version": "20.2.0"}]
    }
    with open(pipeline2_dir / "dataset_description.json", "w") as f:
        json.dump(pipeline2_desc, f)
    
    # Only sub-01 has data in pipeline2
    anat_dir = pipeline2_dir / "analysis" / "sub-01" / "ses-pre" / "anat"
    anat_dir.mkdir(parents=True)
    (anat_dir / "sub-01_ses-pre_desc-preproc_T1w.nii.gz").write_text("preprocessed")
    
    return dataset_root


@pytest.fixture
def mock_no_session_derivatives(tmp_path):
    """
    Create dataset with derivatives that have no sessions.
    
    Structure:
        dataset/
            sub-01/
                anat/
                    sub-01_T1w.nii.gz
            derivatives/
                pipeline1/
                    sub-01/
                        anat/
                            sub-01_space-MNI_T1w.nii.gz
    """
    dataset_root = tmp_path / "no_session_dataset"
    dataset_root.mkdir()
    
    # Dataset description
    desc = {"Name": "No Session Dataset", "BIDSVersion": "1.8.0"}
    with open(dataset_root / "dataset_description.json", "w") as f:
        json.dump(desc, f)
    
    # Raw data (no sessions)
    anat_dir = dataset_root / "sub-01" / "anat"
    anat_dir.mkdir(parents=True)
    (anat_dir / "sub-01_T1w.nii.gz").write_text("raw")
    
    # Derivatives (no sessions)
    pipeline_dir = dataset_root / "derivatives" / "pipeline1"
    pipeline_dir.mkdir(parents=True)
    
    desc = {"Name": "Pipeline 1", "BIDSVersion": "1.8.0"}
    with open(pipeline_dir / "dataset_description.json", "w") as f:
        json.dump(desc, f)
    
    deriv_anat = pipeline_dir / "sub-01" / "anat"
    deriv_anat.mkdir(parents=True)
    (deriv_anat / "sub-01_space-MNI_T1w.nii.gz").write_text("normalized")
    
    return dataset_root


class TestDerivativeLoading:
    """Test loading derivatives from filesystem."""
    
    def test_load_dataset_with_derivatives(self, mock_derivatives_dataset):
        """Test that derivatives are loaded when present."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        # Check that subjects have derivatives
        assert len(dataset.subjects) == 2
        
        for subject in dataset.subjects:
            assert len(subject.derivatives) > 0
    
    def test_derivatives_structure(self, mock_derivatives_dataset):
        """Test that derivative structure is correct."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject_01 = dataset.get_subject("01")
        assert subject_01 is not None
        
        # Should have 2 pipelines
        assert len(subject_01.derivatives) == 2
        
        # Check pipeline names
        pipeline_names = {d.pipeline_name for d in subject_01.derivatives}
        assert pipeline_names == {"pipeline1", "pipeline2"}
    
    def test_derivative_pipeline_description(self, mock_derivatives_dataset):
        """Test that pipeline descriptions are loaded."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline1 = subject.get_derivative("pipeline1")
        
        assert pipeline1 is not None
        assert pipeline1.pipeline_description is not None
        assert pipeline1.pipeline_description["Name"] == "Pipeline 1"
        assert "PipelineDescription" in pipeline1.pipeline_description
        assert "GeneratedBy" in pipeline1.pipeline_description
    
    def test_derivative_sessions(self, mock_derivatives_dataset):
        """Test that derivative sessions are loaded."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject_01 = dataset.get_subject("01")
        assert subject_01 is not None
        pipeline1 = subject_01.get_derivative("pipeline1")
        assert pipeline1 is not None
        
        # Should have ses-pre
        assert len(pipeline1.sessions) == 1
        assert pipeline1.sessions[0].session_id == "pre"
    
    def test_derivative_files(self, mock_derivatives_dataset):
        """Test that derivative files are loaded."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline1 = subject.get_derivative("pipeline1")
        assert pipeline1 is not None
        
        # Check session files
        session = pipeline1.sessions[0]
        assert len(session.files) > 0
        
        # Verify file properties
        nifti_files = [f for f in session.files if f.extension == ".nii.gz"]
        assert len(nifti_files) > 0
        
        # Check that file has correct entities
        space_file = next((f for f in nifti_files if "space" in f.entities), None)
        assert space_file is not None
        assert space_file.entities["space"] == "MNI"
    
    def test_nested_derivative_structure(self, mock_derivatives_dataset):
        """Test derivatives with nested subdirectories (e.g., analysis/)."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject_01 = dataset.get_subject("01")
        assert subject_01 is not None
        pipeline2 = subject_01.get_derivative("pipeline2")
        
        # Should find subject even in nested structure
        assert pipeline2 is not None
        assert len(pipeline2.sessions) == 1
        assert len(pipeline2.sessions[0].files) > 0
    
    def test_subject_without_derivatives(self, mock_derivatives_dataset):
        """Test that subjects without derivative data have empty list."""
        # Modify dataset so sub-02 has no pipeline2 data
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject_02 = dataset.get_subject("02")
        assert subject_02 is not None
        
        # sub-02 should have pipeline1 but not full pipeline2 data
        assert len(subject_02.derivatives) >= 1
        pipeline1 = subject_02.get_derivative("pipeline1")
        assert pipeline1 is not None
    
    def test_derivatives_without_sessions(self, mock_no_session_derivatives):
        """Test loading derivatives for datasets without sessions."""
        loader = BidsLoader(mock_no_session_derivatives)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        assert len(subject.derivatives) == 1
        
        pipeline = subject.derivatives[0]
        assert pipeline.pipeline_name == "pipeline1"
        
        # Should have no sessions, but files directly
        assert len(pipeline.sessions) == 0
        assert len(pipeline.files) > 0


class TestDerivativeModel:
    """Test BIDSDerivative data model."""
    
    def test_create_derivative(self):
        """Test creating a BIDSDerivative object."""
        derivative = BIDSDerivative(
            pipeline_name="test_pipeline",
            sessions=[],
            files=[],
            pipeline_description={"Name": "Test"}
        )
        
        assert derivative.pipeline_name == "test_pipeline"
        assert derivative.sessions == []
        assert derivative.files == []
        assert derivative.pipeline_description["Name"] == "Test"
    
    def test_derivative_with_sessions(self):
        """Test derivative with sessions."""
        session = BIDSSession(session_id="01", files=[])
        
        derivative = BIDSDerivative(
            pipeline_name="pipeline1",
            sessions=[session],
            files=[],
            pipeline_description={}
        )
        
        assert len(derivative.sessions) == 1
        assert derivative.sessions[0].session_id == "01"
    
    def test_derivative_with_files(self):
        """Test derivative with files (no sessions)."""
        file1 = BIDSFile(
            path=Path("/test/file1.nii.gz"),
            modality="anat",
            suffix="T1w",
            extension=".nii.gz",
            entities={"space": "MNI"}
        )
        
        derivative = BIDSDerivative(
            pipeline_name="pipeline1",
            sessions=[],
            files=[file1],
            pipeline_description={}
        )
        
        assert len(derivative.files) == 1
        assert derivative.files[0].entities["space"] == "MNI"


class TestDerivativeDatasetMethods:
    """Test BIDSDataset methods for derivatives."""
    
    def test_get_all_derivative_pipelines(self, mock_derivatives_dataset):
        """Test getting all derivative pipeline names."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        pipelines = dataset.get_all_derivative_pipelines()
        
        assert len(pipelines) == 2
        assert "pipeline1" in pipelines
        assert "pipeline2" in pipelines
    
    def test_get_all_derivative_pipelines_empty(self, tmp_path):
        """Test getting pipelines when there are no derivatives."""
        # Create minimal dataset without derivatives
        dataset_root = tmp_path / "no_deriv"
        dataset_root.mkdir()
        
        desc = {"Name": "Test", "BIDSVersion": "1.8.0"}
        with open(dataset_root / "dataset_description.json", "w") as f:
            json.dump(desc, f)
        
        anat_dir = dataset_root / "sub-01" / "anat"
        anat_dir.mkdir(parents=True)
        (anat_dir / "sub-01_T1w.nii.gz").write_text("data")
        
        loader = BidsLoader(dataset_root)
        dataset = loader.load()
        
        pipelines = dataset.get_all_derivative_pipelines()
        assert len(pipelines) == 0


class TestSubjectDerivativeMethods:
    """Test BIDSSubject methods for derivatives."""
    
    def test_get_derivative(self, mock_derivatives_dataset):
        """Test getting a specific derivative by name."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline1 = subject.get_derivative("pipeline1")
        
        assert pipeline1 is not None
        assert pipeline1.pipeline_name == "pipeline1"
    
    def test_get_derivative_not_found(self, mock_derivatives_dataset):
        """Test getting a non-existent derivative returns None."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        nonexistent = subject.get_derivative("nonexistent_pipeline")
        
        assert nonexistent is None
    
    def test_derivatives_field(self, mock_derivatives_dataset):
        """Test that derivatives field is properly populated."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        
        assert hasattr(subject, 'derivatives')
        assert isinstance(subject.derivatives, list)
        assert len(subject.derivatives) > 0
        assert all(isinstance(d, BIDSDerivative) for d in subject.derivatives)


class TestDerivativeEntityExtraction:
    """Test entity extraction from derivative files."""
    
    def test_space_entity(self, mock_derivatives_dataset):
        """Test that space entity is extracted correctly."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline1 = subject.get_derivative("pipeline1")
        assert pipeline1 is not None
        
        session = pipeline1.sessions[0]
        space_files = [f for f in session.files if "space" in f.entities]
        
        assert len(space_files) > 0
        assert space_files[0].entities["space"] == "MNI"
    
    def test_desc_entity(self, mock_derivatives_dataset):
        """Test that desc entity is extracted correctly."""
        loader = BidsLoader(mock_derivatives_dataset)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline2 = subject.get_derivative("pipeline2")
        assert pipeline2 is not None
        
        session = pipeline2.sessions[0]
        desc_files = [f for f in session.files if "desc" in f.entities]
        
        assert len(desc_files) > 0
        assert desc_files[0].entities["desc"] == "preproc"


class TestDerivativeEdgeCases:
    """Test edge cases and error handling for derivatives."""
    
    def test_missing_pipeline_description(self, tmp_path):
        """Test handling of missing dataset_description.json in pipeline."""
        dataset_root = tmp_path / "missing_desc"
        dataset_root.mkdir()
        
        # Minimal dataset
        desc = {"Name": "Test", "BIDSVersion": "1.8.0"}
        with open(dataset_root / "dataset_description.json", "w") as f:
            json.dump(desc, f)
        
        # Raw data
        anat_dir = dataset_root / "sub-01" / "anat"
        anat_dir.mkdir(parents=True)
        (anat_dir / "sub-01_T1w.nii.gz").write_text("data")
        
        # Derivative without dataset_description.json
        deriv_anat = dataset_root / "derivatives" / "pipeline1" / "sub-01" / "anat"
        deriv_anat.mkdir(parents=True)
        (deriv_anat / "sub-01_space-MNI_T1w.nii.gz").write_text("normalized")
        
        # Should load without errors
        loader = BidsLoader(dataset_root)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline = subject.get_derivative("pipeline1")
        
        assert pipeline is not None
        assert pipeline.pipeline_description == {}
    
    def test_empty_derivatives_folder(self, tmp_path):
        """Test handling of empty derivatives folder."""
        dataset_root = tmp_path / "empty_deriv"
        dataset_root.mkdir()
        
        desc = {"Name": "Test", "BIDSVersion": "1.8.0"}
        with open(dataset_root / "dataset_description.json", "w") as f:
            json.dump(desc, f)
        
        anat_dir = dataset_root / "sub-01" / "anat"
        anat_dir.mkdir(parents=True)
        (anat_dir / "sub-01_T1w.nii.gz").write_text("data")
        
        # Create empty derivatives folder
        (dataset_root / "derivatives").mkdir()
        
        # Should load without errors
        loader = BidsLoader(dataset_root)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        assert len(subject.derivatives) == 0
    
    def test_malformed_derivative_structure(self, tmp_path):
        """Test handling of malformed derivative structure."""
        dataset_root = tmp_path / "malformed"
        dataset_root.mkdir()
        
        desc = {"Name": "Test", "BIDSVersion": "1.8.0"}
        with open(dataset_root / "dataset_description.json", "w") as f:
            json.dump(desc, f)
        
        anat_dir = dataset_root / "sub-01" / "anat"
        anat_dir.mkdir(parents=True)
        (anat_dir / "sub-01_T1w.nii.gz").write_text("data")
        
        # Create pipeline directory with files but no sub-XX structure
        pipeline_dir = dataset_root / "derivatives" / "pipeline1"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "random_file.txt").write_text("random")
        
        # Should load without crashing
        loader = BidsLoader(dataset_root)
        dataset = loader.load()
        
        subject = dataset.get_subject("01")
        assert subject is not None
        # Subject should have no derivatives since structure is wrong
        pipeline = subject.get_derivative("pipeline1")
        assert pipeline is None or len(pipeline.files) == 0
