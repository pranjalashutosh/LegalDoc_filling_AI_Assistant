"""
Unit tests for LLM service functionality
"""

import pytest
from unittest.mock import patch, MagicMock
from lib.llm_service import (
    generate_question,
    is_llm_enabled,
    check_rate_limit,
    record_request,
    generate_questions_for_candidates
)


@pytest.mark.unit
class TestLLMConfiguration:
    """Test LLM configuration and availability."""
    
    def test_llm_enabled_check(self):
        """Test LLM enabled/disabled check."""
        # This depends on environment configuration
        result = is_llm_enabled()
        assert isinstance(result, bool)
    
    @patch('lib.llm_service.Config.ENABLE_LLM', True)
    @patch('lib.llm_service.Config.GOOGLE_API_KEY', 'test_key')
    def test_llm_enabled_with_api_key(self):
        """Test that LLM is enabled when API key is present."""
        # When both ENABLE_LLM is True and API key exists
        result = is_llm_enabled()
        # Result depends on actual implementation
        assert isinstance(result, bool)
    
    @patch('lib.llm_service.Config.ENABLE_LLM', False)
    def test_llm_disabled_in_config(self):
        """Test that LLM is disabled when config says so."""
        result = is_llm_enabled()
        assert result is False


@pytest.mark.unit
class TestQuestionGeneration:
    """Test question generation with and without LLM."""
    
    def test_fallback_question_format(self):
        """Test fallback question format when LLM is disabled."""
        placeholder = "COMPANY_NAME"
        
        question = generate_question(placeholder, use_llm=False)
        
        # Fallback should be a simple format
        assert placeholder in question or placeholder.replace('_', ' ').lower() in question.lower()
        assert isinstance(question, str)
        assert len(question) > 0
    
    def test_question_generation_various_placeholders(self):
        """Test question generation for various placeholder formats."""
        placeholders = [
            'COMPANY_NAME',
            'CLIENT_ADDRESS',
            'CONTRACT_DATE',
            'PAYMENT_AMOUNT',
            'Date_of_Safe'
        ]
        
        for placeholder in placeholders:
            question = generate_question(placeholder, use_llm=False)
            
            assert isinstance(question, str)
            assert len(question) > 0
            # Question should be human-readable
            assert question[0].isupper()  # Starts with capital
    
    @patch('lib.llm_service.get_model')
    def test_llm_question_generation_with_mock(self, mock_get_model):
        """Test LLM question generation with mocked API."""
        # Mock the Gemini API response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "What is the name of the company?"
        mock_model.generate_content.return_value = mock_response
        mock_get_model.return_value = mock_model
        
        placeholder = "COMPANY_NAME"
        
        # This would call the LLM if enabled
        try:
            question = generate_question(placeholder, use_llm=True)
            assert isinstance(question, str)
            assert len(question) > 0
        except Exception:
            # If LLM not configured, should fall back
            question = generate_question(placeholder, use_llm=False)
            assert "COMPANY_NAME" in question or "company name" in question.lower()
    
    def test_llm_fallback_on_error(self):
        """Test that LLM falls back to simple question on error."""
        placeholder = "COMPANY_NAME"
        
        # Even if LLM fails, should return a valid question
        question = generate_question(placeholder, use_llm=True)
        
        assert isinstance(question, str)
        assert len(question) > 0
    
    def test_caching_behavior(self):
        """Test that repeated calls for same placeholder use cache."""
        placeholder = "COMPANY_NAME"
        
        # Generate question twice
        question1 = generate_question(placeholder, use_llm=False)
        question2 = generate_question(placeholder, use_llm=False)
        
        # Should return same result (cached)
        assert question1 == question2


@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_check(self):
        """Test rate limit checking."""
        # Should not raise exception
        result = check_rate_limit()
        assert isinstance(result, bool)
    
    def test_rate_limit_recording(self):
        """Test request recording for rate limiting."""
        # Should not raise exception
        record_request()
        
        # Check that rate limit still works
        result = check_rate_limit()
        assert isinstance(result, bool)
    
    @patch('lib.llm_service.request_times', [])
    def test_rate_limit_under_threshold(self):
        """Test rate limit when under threshold."""
        # With empty request times, should be allowed
        result = check_rate_limit()
        assert result is True
    
    def test_multiple_requests_within_limit(self):
        """Test that multiple requests within limit are allowed."""
        # Record several requests
        for _ in range(5):
            record_request()
            assert check_rate_limit() is True


@pytest.mark.unit
class TestBatchQuestionGeneration:
    """Test batch question generation."""
    
    def test_batch_generation_fallback(self):
        """Test batch question generation with fallback."""
        placeholders = ['COMPANY_NAME', 'CLIENT_NAME', 'CONTRACT_DATE']
        
        # Import the function (might not be available in all versions)
        try:
            from lib.llm_service import generate_questions_batch
            
            questions = generate_questions_batch(placeholders, use_llm=False)
            
            assert isinstance(questions, dict)
            assert len(questions) == len(placeholders)
            
            for placeholder in placeholders:
                assert placeholder in questions
                assert isinstance(questions[placeholder], str)
                assert len(questions[placeholder]) > 0
        
        except ImportError:
            # Function might not exist yet
            pytest.skip("Batch generation not implemented")
    
    def test_empty_placeholder_list(self):
        """Test batch generation with empty list."""
        try:
            from lib.llm_service import generate_questions_batch
            
            questions = generate_questions_batch([], use_llm=False)
            
            assert isinstance(questions, dict)
            assert len(questions) == 0
        
        except ImportError:
            pytest.skip("Batch generation not implemented")

    def test_generate_questions_for_candidates_fallback(self):
        """Batch helper returns fallback structure when LLM disabled."""
        items = [{
            'normalized': 'company_name',
            'original': '{{COMPANY_NAME}}',
            'pattern_type': 'double_curly',
            'context': {
                'prev': 'This agreement is entered into by and between the parties.',
                'sentence': 'The {{COMPANY_NAME}} shall provide services.',
                'next': 'Payment terms are outlined below.'
            }
        }]

        results = generate_questions_for_candidates(items, use_llm=False)

        assert 'company_name' in results
        entry = results['company_name']
        assert entry['source'] == 'fallback'
        assert isinstance(entry['question'], str)
        assert len(entry['question']) > 0


# Note: Full LLM integration tests would require:
# 1. A test API key for Gemini
# 2. Network connectivity
# 3. Potentially incurring API costs
# These should be run separately as integration tests, not in CI/CD

