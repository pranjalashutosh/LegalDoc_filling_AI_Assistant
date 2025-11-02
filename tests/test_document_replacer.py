"""
Unit tests for document replacement functionality
"""

import pytest
import os
import tempfile
from pathlib import Path
from lib.document_replacer import (
    get_normalized_placeholder_name,
    validate_document_path,
    DocumentReplacementError
)


@pytest.mark.unit
class TestPlaceholderNormalization:
    """Test placeholder name normalization for document replacement."""
    
    def test_normalize_double_curly(self):
        """Test normalization of {{PLACEHOLDER}} format."""
        assert get_normalized_placeholder_name('{{COMPANY_NAME}}') == 'COMPANY_NAME'
        assert get_normalized_placeholder_name('{{Company Name}}') == 'COMPANY_NAME'
    
    def test_normalize_single_curly(self):
        """Test normalization of {PLACEHOLDER} format."""
        assert get_normalized_placeholder_name('{CLIENT_NAME}') == 'CLIENT_NAME'
        assert get_normalized_placeholder_name('{client name}') == 'CLIENT_NAME'
    
    def test_normalize_square_brackets(self):
        """Test normalization of [Placeholder] format."""
        assert get_normalized_placeholder_name('[Date of Safe]') == 'Date_of_Safe'
        assert get_normalized_placeholder_name('[Party Name]') == 'Party_Name'
    
    def test_normalize_underscores(self):
        """Test normalization of _____ format."""
        assert get_normalized_placeholder_name('_____') == 'UNDERSCORE_PLACEHOLDER'
        assert get_normalized_placeholder_name('________') == 'UNDERSCORE_PLACEHOLDER'
    
    def test_normalize_dollar_brackets(self):
        """Test normalization of $[_____] format."""
        assert get_normalized_placeholder_name('$[_____]') == 'DOLLAR_BRACKET_PLACEHOLDER'
    
    def test_normalize_spaces_to_underscores(self):
        """Test that spaces are converted to underscores."""
        assert get_normalized_placeholder_name('COMPANY NAME') == 'COMPANY_NAME'
        assert get_normalized_placeholder_name('Date of Safe') == 'Date_of_Safe'


@pytest.mark.unit
class TestDocumentPathValidation:
    """Test document path validation."""
    
    def test_validate_empty_path(self):
        """Test validation of empty path."""
        with pytest.raises(DocumentReplacementError, match="File path is required"):
            validate_document_path('')
    
    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file."""
        with pytest.raises(DocumentReplacementError, match="File not found"):
            validate_document_path('/path/to/nonexistent/file.docx')
    
    def test_validate_directory_path(self):
        """Test validation when path is a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(DocumentReplacementError, match="Path is not a file"):
                validate_document_path(tmpdir)
    
    def test_validate_non_docx_file(self):
        """Test validation of non-.docx file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmpfile:
            try:
                with pytest.raises(DocumentReplacementError, match="must be a .docx document"):
                    validate_document_path(tmpfile.name)
            finally:
                os.unlink(tmpfile.name)
    
    def test_validate_valid_docx_path(self):
        """Test validation of valid .docx path."""
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmpfile:
            tmpfile.write(b'dummy content')
            tmpfile.flush()
            
            try:
                # Should not raise exception
                result = validate_document_path(tmpfile.name)
                assert result is True
            finally:
                os.unlink(tmpfile.name)


@pytest.mark.unit
class TestDocumentReplacement:
    """Test document replacement functionality (requires actual .docx files)."""
    
    def test_replacement_preserves_formatting_mock(self):
        """
        Test that replacement would preserve formatting.
        This is a placeholder for integration tests with actual .docx files.
        """
        # This would require creating actual .docx files with formatting
        # For now, we document the expected behavior
        pass
    
    def test_all_pattern_types_replaced_mock(self):
        """
        Test that all 5 pattern types are replaced correctly.
        This is a placeholder for integration tests with actual .docx files.
        """
        # This would require creating test .docx files with all pattern types
        pass
    
    def test_run_level_replacement_mock(self):
        """
        Test that replacement happens at run level, not paragraph level.
        This is a placeholder for integration tests with actual .docx files.
        """
        # This would require creating test .docx files with complex formatting
        pass


# Note: Full document replacement tests require actual .docx test fixtures
# These would be integration tests that:
# 1. Create a sample .docx with various placeholders and formatting
# 2. Replace placeholders with values
# 3. Open the result and verify:
#    - All placeholders are replaced
#    - Formatting is preserved (bold, italic, fonts, etc.)
#    - Document structure is intact (tables, lists, etc.)

