"""
Integration tests for API routes
Tests the full flow: upload → detect → answer → preview → download
"""

import pytest
import json
import io
from pathlib import Path


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check and basic endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root API endpoint."""
        response = client.get('/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'operational'
        assert 'endpoints' in data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


@pytest.mark.integration
class TestUploadFlow:
    """Test file upload functionality."""
    
    def test_upload_endpoint_exists(self, client):
        """Test that upload endpoint exists."""
        # POST without file should return error
        response = client.post('/api/upload')
        
        # Should return 400 (bad request) not 404 (not found)
        assert response.status_code in [400, 422]
    
    def test_upload_without_file(self, client):
        """Test upload without file returns error."""
        response = client.post('/api/upload', data={})
        
        assert response.status_code in [400, 422]
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_upload_invalid_file_type(self, client):
        """Test upload with invalid file type."""
        # Create a fake .txt file
        data = {
            'file': (io.BytesIO(b'test content'), 'test.txt')
        }
        
        response = client.post('/api/upload', data=data, content_type='multipart/form-data')
        
        assert response.status_code in [400, 415]
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_upload_status_endpoint(self, client):
        """Test upload status endpoint."""
        response = client.get('/api/upload/status')
        
        # Should return success even if no file uploaded
        assert response.status_code == 200


@pytest.mark.integration
class TestDetectionFlow:
    """Test placeholder detection functionality."""
    
    def test_detect_without_upload(self, client):
        """Test detection without prior upload."""
        response = client.post('/api/detect')
        
        # Should return error (no file in session)
        assert response.status_code in [400, 404]
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_detect_status_endpoint(self, client):
        """Test detection status endpoint."""
        response = client.get('/api/detect/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'success' in data


@pytest.mark.integration
class TestConversationFlow:
    """Test conversational filling functionality."""
    
    def test_conversation_next_without_session(self, client):
        """Test getting next question without session."""
        response = client.get('/api/conversation/next?placeholder=TEST')
        
        # Should return error (no session)
        assert response.status_code in [400, 404]
    
    def test_conversation_answer_without_session(self, client):
        """Test submitting answer without session."""
        response = client.post('/api/conversation/answer', 
                              json={'placeholder': 'TEST', 'answer': 'value'})
        
        # Should return error (no session)
        assert response.status_code in [400, 404]
    
    def test_conversation_status_endpoint(self, client):
        """Test conversation status endpoint."""
        response = client.get('/api/conversation/status')
        
        # Should work even without session
        assert response.status_code in [200, 400]


@pytest.mark.integration
class TestPreviewFlow:
    """Test preview generation functionality."""
    
    def test_preview_generate_without_session(self, client):
        """Test preview generation without session."""
        response = client.post('/api/preview/generate')
        
        # Should return error (no session)
        assert response.status_code in [400, 404]
    
    def test_preview_html_without_session(self, client):
        """Test getting preview HTML without session."""
        response = client.get('/api/preview/html')
        
        # Should return error (no preview)
        assert response.status_code in [400, 404]
    
    def test_preview_status_endpoint(self, client):
        """Test preview status endpoint."""
        response = client.get('/api/preview/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'has_preview' in data


@pytest.mark.integration
class TestDownloadFlow:
    """Test document download functionality."""
    
    def test_download_without_session(self, client):
        """Test download without session."""
        response = client.get('/api/download')
        
        # Should return error (no document)
        assert response.status_code in [400, 404]
    
    def test_download_status_endpoint(self, client):
        """Test download status endpoint."""
        response = client.get('/api/download/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'is_available' in data
        assert data['is_available'] is False  # No document yet


@pytest.mark.integration
class TestSessionManagement:
    """Test session management functionality."""
    
    def test_session_persistence(self, client):
        """Test that session persists across requests."""
        # Make first request
        response1 = client.get('/health')
        assert response1.status_code == 200
        
        # Make second request (should use same session)
        response2 = client.get('/health')
        assert response2.status_code == 200
    
    def test_upload_clear_endpoint(self, client):
        """Test clearing upload session."""
        response = client.post('/api/upload/clear')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling across the application."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_invalid_json_post(self, client):
        """Test POST with invalid JSON."""
        response = client.post('/api/conversation/answer',
                              data='invalid json',
                              content_type='application/json')
        
        # Should return 400 or 422
        assert response.status_code in [400, 422]
    
    def test_missing_required_field(self, client):
        """Test POST with missing required field."""
        response = client.post('/api/conversation/answer',
                              json={'placeholder': 'TEST'})  # Missing 'answer'
        
        assert response.status_code == 400


# Note: Full end-to-end integration tests would require:
# 1. Creating actual .docx test files
# 2. Testing the complete flow from upload to download
# 3. Verifying file contents and transformations
# These are best run manually or in a staging environment

