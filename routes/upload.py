"""
File upload routes for Legal Document Filler.
Handles .docx file uploads with validation.
"""

from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from lib.validators import validate_file, sanitize_filename, FileValidationError
import os
import uuid
from datetime import datetime

# Create blueprint
upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload endpoint.
    
    Expected:
        - File with key 'file' in multipart/form-data
    
    Returns:
        JSON response with upload status and session info
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'message': 'Please select a .docx file to upload.'
            }), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'message': 'Please select a file before uploading.'
            }), 400
        
        # Get configuration
        max_size_bytes = current_app.config.get('MAX_FILE_SIZE_BYTES', 5 * 1024 * 1024)
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'.docx'})
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Validate file
        try:
            validation_result = validate_file(file, max_size_bytes, allowed_extensions)
        except FileValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'message': str(e)
            }), 400
        
        # Generate unique session ID if not exists
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session['created_at'] = datetime.utcnow().isoformat()
        
        session_id = session['session_id']
        
        # Sanitize and secure filename
        original_filename = file.filename
        safe_filename = sanitize_filename(secure_filename(original_filename))
        
        # Create unique filename with session ID
        name, ext = os.path.splitext(safe_filename)
        unique_filename = f"{session_id}_{name}{ext}"
        
        # Create session-specific upload directory
        session_upload_dir = os.path.join(upload_folder, session_id)
        os.makedirs(session_upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(session_upload_dir, unique_filename)
        file.save(file_path)
        
        # Store file information in session
        session['uploaded_file'] = {
            'original_filename': original_filename,
            'safe_filename': safe_filename,
            'unique_filename': unique_filename,
            'file_path': file_path,
            'size_bytes': validation_result['size_bytes'],
            'size_mb': validation_result['size_mb'],
            'uploaded_at': datetime.utcnow().isoformat()
        }
        
        # Update last activity
        session['last_activity'] = datetime.utcnow().isoformat()
        
        # Mark session as permanent (for timeout)
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'session_id': session_id,
            'filename': original_filename,
            'size_mb': validation_result['size_mb'],
            'uploaded_at': session['uploaded_file']['uploaded_at']
        }), 200
    
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"Upload error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Upload failed',
            'message': 'An unexpected error occurred during upload. Please try again.'
        }), 500


@upload_bp.route('/upload/status', methods=['GET'])
def upload_status():
    """
    Check upload status for current session.
    
    Returns:
        JSON response with upload status
    """
    try:
        if 'session_id' not in session or 'uploaded_file' not in session:
            return jsonify({
                'success': True,
                'uploaded': False,
                'message': 'No file uploaded in this session'
            }), 200
        
        file_info = session['uploaded_file']
        
        # Check if file still exists
        file_path = file_info.get('file_path')
        file_exists = os.path.exists(file_path) if file_path else False
        
        return jsonify({
            'success': True,
            'uploaded': file_exists,
            'session_id': session['session_id'],
            'filename': file_info.get('original_filename'),
            'size_mb': file_info.get('size_mb'),
            'uploaded_at': file_info.get('uploaded_at')
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Status check error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Status check failed',
            'message': 'Unable to check upload status'
        }), 500


@upload_bp.route('/upload/clear', methods=['POST'])
def clear_upload():
    """
    Clear uploaded file from session and delete from disk.
    
    Returns:
        JSON response with clear status
    """
    try:
        if 'uploaded_file' in session:
            file_info = session['uploaded_file']
            file_path = file_info.get('file_path')
            
            # Delete file if it exists
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    current_app.logger.warning(f"Failed to delete file {file_path}: {e}")
            
            # Remove from session
            session.pop('uploaded_file', None)
        
        return jsonify({
            'success': True,
            'message': 'Upload cleared successfully'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Clear upload error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Clear failed',
            'message': 'Unable to clear upload'
        }), 500

