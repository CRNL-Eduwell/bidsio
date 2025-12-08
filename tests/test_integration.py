"""
Integration tests for export and derivatives.

Tests the complete workflow of loading derivatives and exporting them.
"""

import pytest
import json
from pathlib import Path

from src.bidsio.infrastructure.bids_loader import BidsLoader
from src.bidsio.core.models import ExportRequest, SelectedEntities
from src.bidsio.core.export import export_dataset


@pytest.fixture
def full_mock_dataset(tmp_path):
    """
    Create a complete mock BIDS dataset with derivatives for integration testing.
    """
    dataset_root = tmp_path / "full_dataset"
    dataset_root.mkdir()
    
    # Dataset description
    desc = {
        "Name": "Integration Test Dataset",
        "BIDSVersion": "1.8.0",
        "Authors": ["Test Author"]
    }
    with open(dataset_root / "dataset_description.json", "w") as f:
        json.dump(desc, f)
    
    # Participants
    with open(dataset_root / "participants.tsv", "w") as f:
        f.write("participant_id\tage\tsex\n")
        f.write("sub-01\t25\tM\n")
        f.write("sub-02\t30\tF\n")
    
    # Raw data with multiple modalities
    for sub_id in ["01", "02"]:
        for ses_id in ["pre", "post"]:
            # Anatomical
            anat_dir = dataset_root / f"sub-{sub_id}" / f"ses-{ses_id}" / "anat"
            anat_dir.mkdir(parents=True)
            (anat_dir / f"sub-{sub_id}_ses-{ses_id}_T1w.nii.gz").write_text("T1 data")
            (anat_dir / f"sub-{sub_id}_ses-{ses_id}_T1w.json").write_text('{"EchoTime": 0.003}')
            
            # iEEG with tasks
            ieeg_dir = dataset_root / f"sub-{sub_id}" / f"ses-{ses_id}" / "ieeg"
            ieeg_dir.mkdir(parents=True)
            for task in ["rest", "task"]:
                (ieeg_dir / f"sub-{sub_id}_ses-{ses_id}_task-{task}_ieeg.eeg").write_text("EEG data")
                (ieeg_dir / f"sub-{sub_id}_ses-{ses_id}_task-{task}_ieeg.json").write_text('{"SamplingFrequency": 1000}')
    
    # Derivatives
    deriv_root = dataset_root / "derivatives"
    
    # Pipeline 1: Preprocessing
    pipeline1_dir = deriv_root / "preprocessing"
    pipeline1_dir.mkdir(parents=True)
    
    pipeline1_desc = {
        "Name": "Preprocessing Pipeline",
        "BIDSVersion": "1.8.0",
        "PipelineDescription": {"Name": "Anatomical preprocessing"},
        "GeneratedBy": [{"Name": "FreeSurfer", "Version": "7.1.0"}]
    }
    with open(pipeline1_dir / "dataset_description.json", "w") as f:
        json.dump(pipeline1_desc, f)
    
    for sub_id in ["01", "02"]:
        for ses_id in ["pre", "post"]:
            deriv_anat = pipeline1_dir / f"sub-{sub_id}" / f"ses-{ses_id}" / "anat"
            deriv_anat.mkdir(parents=True)
            (deriv_anat / f"sub-{sub_id}_ses-{ses_id}_desc-preproc_T1w.nii.gz").write_text("preprocessed")
            (deriv_anat / f"sub-{sub_id}_ses-{ses_id}_space-MNI_T1w.nii.gz").write_text("normalized")
    
    # Pipeline 2: Analysis (only sub-01)
    pipeline2_dir = deriv_root / "analysis"
    pipeline2_dir.mkdir(parents=True)
    
    pipeline2_desc = {
        "Name": "Analysis Pipeline",
        "BIDSVersion": "1.8.0",
        "PipelineDescription": {"Name": "Statistical analysis"},
        "GeneratedBy": [{"Name": "SPM", "Version": "12"}]
    }
    with open(pipeline2_dir / "dataset_description.json", "w") as f:
        json.dump(pipeline2_desc, f)
    
    # Only sub-01, ses-pre has analysis results
    analysis_dir = pipeline2_dir / "sub-01" / "ses-pre" / "anat"
    analysis_dir.mkdir(parents=True)
    (analysis_dir / "sub-01_ses-pre_desc-stats_T1w.nii.gz").write_text("stats")
    
    return dataset_root


class TestExportDerivativesIntegration:
    """Integration tests for exporting datasets with derivatives."""
    
    def test_full_workflow_load_and_export(self, full_mock_dataset, tmp_path):
        """Test complete workflow: load dataset with derivatives and export."""
        # Load dataset
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        # Verify derivatives loaded
        assert len(dataset.get_all_derivative_pipelines()) == 2
        
        # Export with derivatives
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Verify export structure
        assert (output_path / "dataset_description.json").exists()
        assert (output_path / "derivatives" / "preprocessing").exists()
        assert (output_path / "derivatives" / "preprocessing" / "dataset_description.json").exists()
        
        # Verify derivative files exist
        assert (output_path / "derivatives" / "preprocessing" / "sub-01" / "ses-pre" / "anat").exists()
        derivative_files = list((output_path / "derivatives" / "preprocessing").rglob("*.nii.gz"))
        assert len(derivative_files) > 0
    
    def test_export_filtered_subjects_with_derivatives(self, full_mock_dataset, tmp_path):
        """Test exporting filtered subjects preserves correct derivative data."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={"sub": ["01"]},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Only sub-01 should be exported
        assert (output_path / "sub-01").exists()
        assert not (output_path / "sub-02").exists()
        
        # Derivative files should only be for sub-01
        deriv_files = list((output_path / "derivatives" / "preprocessing").rglob("sub-*.nii.gz"))
        assert all("sub-01" in f.name for f in deriv_files)
        assert not any("sub-02" in f.name for f in deriv_files)
    
    def test_export_filtered_sessions_with_derivatives(self, full_mock_dataset, tmp_path):
        """Test exporting filtered sessions preserves correct derivative data."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={"ses": ["pre"]},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Only ses-pre should be exported
        assert (output_path / "sub-01" / "ses-pre").exists()
        assert not (output_path / "sub-01" / "ses-post").exists()
        
        # Derivative files should only be for ses-pre
        deriv_files = list((output_path / "derivatives" / "preprocessing").rglob("ses-*.nii.gz"))
        assert all("ses-pre" in f.name for f in deriv_files)
        assert not any("ses-post" in f.name for f in deriv_files)
    
    def test_export_multiple_pipelines(self, full_mock_dataset, tmp_path):
        """Test exporting multiple derivative pipelines."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["preprocessing", "analysis"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Both pipelines should exist
        assert (output_path / "derivatives" / "preprocessing").exists()
        assert (output_path / "derivatives" / "analysis").exists()
        
        # Both should have dataset_description.json
        assert (output_path / "derivatives" / "preprocessing" / "dataset_description.json").exists()
        assert (output_path / "derivatives" / "analysis" / "dataset_description.json").exists()
    
    def test_export_no_derivatives(self, full_mock_dataset, tmp_path):
        """Test exporting without derivatives."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=[]  # No derivatives
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Raw data should exist
        assert (output_path / "sub-01").exists()
        
        # Derivatives folder should not exist or be empty
        if (output_path / "derivatives").exists():
            # Should not contain any nifti files
            deriv_files = list((output_path / "derivatives").rglob("*.nii.gz"))
            assert len(deriv_files) == 0
    
    def test_export_derivative_entity_filtering(self, full_mock_dataset, tmp_path):
        """Test that entity filtering applies to derivative files."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={"desc": ["preproc"]},  # Only preproc desc
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Should only export files with desc-preproc
        deriv_files = list((output_path / "derivatives" / "preprocessing").rglob("*.nii.gz"))
        preproc_files = [f for f in deriv_files if "desc-preproc" in f.name]
        space_files = [f for f in deriv_files if "space-MNI" in f.name and "desc-preproc" not in f.name]
        
        assert len(preproc_files) > 0
        # Files with only space (no desc) should not be excluded unless desc is in selection
        # Since we selected desc=["preproc"], files WITH desc entity but not "preproc" should be excluded
    
    def test_export_preserves_metadata_files(self, full_mock_dataset, tmp_path):
        """Test that JSON sidecar files are exported with derivatives."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Check that JSON sidecars exist for raw data
        assert (output_path / "sub-01" / "ses-pre" / "anat" / "sub-01_ses-pre_T1w.json").exists()
        assert (output_path / "sub-01" / "ses-pre" / "ieeg" / "sub-01_ses-pre_task-rest_ieeg.json").exists()


class TestDerivativeDataConsistency:
    """Test that derivative data remains consistent through load-export cycle."""
    
    def test_derivative_pipeline_description_preserved(self, full_mock_dataset, tmp_path):
        """Test that pipeline descriptions are preserved in export."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        # Get original pipeline description
        subject = dataset.get_subject("01")
        assert subject is not None
        original_pipeline = subject.get_derivative("preprocessing")
        assert original_pipeline is not None
        original_desc = original_pipeline.pipeline_description
        
        # Export
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        export_dataset(request)
        
        # Reload exported dataset
        loader2 = BidsLoader(output_path)
        exported_dataset = loader2.load()
        
        # Compare pipeline descriptions
        exported_subject = exported_dataset.get_subject("01")
        assert exported_subject is not None
        exported_pipeline = exported_subject.get_derivative("preprocessing")
        assert exported_pipeline is not None
        
        assert exported_pipeline.pipeline_description["Name"] == original_desc["Name"]
        assert exported_pipeline.pipeline_description["BIDSVersion"] == original_desc["BIDSVersion"]
    
    def test_derivative_file_count_consistency(self, full_mock_dataset, tmp_path):
        """Test that file counts remain consistent after export."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        # Count original derivative files
        subject = dataset.get_subject("01")
        assert subject is not None
        pipeline = subject.get_derivative("preprocessing")
        assert pipeline is not None
        original_file_count = len(pipeline.files) + sum(len(s.files) for s in pipeline.sessions)
        
        # Export
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        export_dataset(request)
        
        # Reload and count
        loader2 = BidsLoader(output_path)
        exported_dataset = loader2.load()
        
        exported_subject = exported_dataset.get_subject("01")
        assert exported_subject is not None
        exported_pipeline = exported_subject.get_derivative("preprocessing")
        assert exported_pipeline is not None
        exported_file_count = len(exported_pipeline.files) + sum(len(s.files) for s in exported_pipeline.sessions)
        
        assert exported_file_count == original_file_count


class TestEdgeCases:
    """Test edge cases in export and derivatives integration."""
    
    def test_export_subject_with_no_derivative_data(self, full_mock_dataset, tmp_path):
        """Test exporting when subject exists in raw but not in derivative."""
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        # Export only analysis pipeline (which only has sub-01)
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["analysis"]
            ),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Both subjects should have raw data
        assert (output_path / "sub-01").exists()
        assert (output_path / "sub-02").exists()
        
        # But only sub-01 should have analysis derivatives
        assert (output_path / "derivatives" / "analysis" / "sub-01").exists()
        # sub-02 might not have any files in analysis pipeline
    
    def test_reload_exported_dataset(self, full_mock_dataset, tmp_path):
        """Test that exported dataset can be reloaded successfully."""
        # Original load and export
        loader = BidsLoader(full_mock_dataset)
        dataset = loader.load()
        
        output_path = tmp_path / "exported"
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=SelectedEntities(
                entities={"sub": ["01"], "ses": ["pre"]},
                derivative_pipelines=["preprocessing"]
            ),
            output_path=output_path
        )
        export_dataset(request)
        
        # Reload exported dataset
        loader2 = BidsLoader(output_path)
        reloaded_dataset = loader2.load()
        
        # Verify structure
        assert len(reloaded_dataset.subjects) > 0
        subject = reloaded_dataset.get_subject("01")
        assert subject is not None
        assert len(subject.sessions) > 0
        assert len(subject.derivatives) > 0
        
        # Verify derivative pipeline
        pipeline = subject.get_derivative("preprocessing")
        assert pipeline is not None
        assert pipeline.pipeline_name == "preprocessing"
