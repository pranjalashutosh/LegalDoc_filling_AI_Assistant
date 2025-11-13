"""
Download API Routes
Handles document download functionality
"""

from flask import Blueprint, request, session, jsonify, send_file, send_from_directory
from lib.error_handlers import handle_api_error, SessionExpiredError
from config import Config
import logging
import os
from werkzeug.utils import secure_filename
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
download_bp = Blueprint('download', __name__)


@download_bp.route('/download', methods=['GET'])
def download_document():
    """
    Download the completed document.
    
    Returns:
        .docx file as attachment
    """
    try:
        # Retrieve completed document info from session
        completed_path = session.get('completed_path')
        completed_filename = session.get('completed_filename')
        
        if not completed_path or not completed_filename:
            raise SessionExpiredError('No completed document available. Please generate preview first.')
        
        if not os.path.exists(completed_path):
            raise SessionExpiredError('Completed document no longer exists. Please regenerate.')
        
        logger.info(f"Serving download: {completed_filename}")
        
        # Send file with appropriate headers
        return send_file(
            completed_path,
            as_attachment=True,
            download_name=completed_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return handle_api_error(e, 'Failed to download document')


@download_bp.route('/download/status', methods=['GET'])
def download_status():
    """
    Check if a document is available for download.
    
    Returns:
        JSON with download availability status
    """
    try:
        completed_path = session.get('completed_path')
        completed_filename = session.get('completed_filename')
        
        is_available = (
            completed_path is not None 
            and completed_filename is not None 
            and os.path.exists(completed_path)
        )
        
        file_size = None
        if is_available:
            try:
                file_size = os.path.getsize(completed_path)
            except Exception as e:
                logger.warning(f"Failed to get file size: {e}")
        
        return jsonify({
            'success': True,
            'is_available': is_available,
            'filename': completed_filename if is_available else None,
            'file_size': file_size
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking download status: {e}")
        return handle_api_error(e, 'Failed to check download status')


@download_bp.route('/download/info', methods=['GET'])
def download_info():
    """
    Get information about the completed document.
    
    Returns:
        JSON with document metadata
    """
    try:
        completed_path = session.get('completed_path')
        completed_filename = session.get('completed_filename')
        answers = session.get('answers', {})
        
        if not completed_path or not completed_filename:
            raise SessionExpiredError('No completed document available')
        
        if not os.path.exists(completed_path):
            raise SessionExpiredError('Completed document no longer exists')
        
        # Get file stats
        file_stats = os.stat(completed_path)
        file_size = file_stats.st_size
        created_time = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
        
        return jsonify({
            'success': True,
            'filename': completed_filename,
            'file_size': file_size,
            'created_at': created_time,
            'total_replacements': len(answers),
            'placeholders_filled': list(answers.keys())
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error getting download info: {e}")
        return handle_api_error(e, 'Failed to get download info')


@download_bp.route('/download/cleanup', methods=['POST'])
def cleanup_download():
    """
    Clean up the completed document after download.
    Optional endpoint - can be called by client after successful download.
    
    Returns:
        JSON with success status
    """
    try:
        completed_path = session.get('completed_path')
        
        if completed_path and os.path.exists(completed_path):
            try:
                os.remove(completed_path)
                logger.info(f"Cleaned up completed document: {completed_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up file: {cleanup_error}")
        
        # Clear download-related session data
        if 'completed_path' in session:
            session.pop('completed_path')
        if 'completed_filename' in session:
            session.pop('completed_filename')
        if 'preview_html' in session:
            session.pop('preview_html')
        
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': 'Download files cleaned up successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up download: {e}")
        return handle_api_error(e, 'Failed to clean up download')

