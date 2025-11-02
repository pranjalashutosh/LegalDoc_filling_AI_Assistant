"""
Preview API Routes
Handles document preview generation and serving
"""

from flask import Blueprint, request, session, jsonify, send_file
from lib.document_replacer import replace_placeholders, DocumentReplacementError
from lib.preview_generator import generate_preview_html, PreviewGenerationError
from lib.error_handlers import handle_api_error, SessionExpiredError
from config import Config
import logging
import os
from datetime import datetime
import tempfile

logger = logging.getLogger(__name__)

# Create blueprint
preview_bp = Blueprint('preview', __name__)


@preview_bp.route('/api/preview/generate', methods=['POST'])
def generate_preview():
    """
    Generate a completed document and HTML preview.
    
    Workflow:
        1. Retrieve uploaded file path from session
        2. Get all answers from session
        3. Replace placeholders in document
        4. Generate HTML preview
        5. Store paths in session
    
    Returns:
        JSON with success status and preview availability
    """
    try:
        # Check session for required data
        filename = session.get('filename')
        answers = session.get('answers', {})
        placeholders = session.get('placeholders', [])
        
        if not filename:
            raise SessionExpiredError('No uploaded file found in session')
        
        if not answers:
            return jsonify({
                'success': False,
                'error': 'No answers provided. Please fill in at least one placeholder.'
            }), 400
        
        # Construct input file path
        upload_folder = Config.UPLOAD_FOLDER
        input_path = os.path.join(upload_folder, filename)
        
        if not os.path.exists(input_path):
            raise SessionExpiredError('Uploaded file no longer exists. Please upload again.')
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(filename)[0]
        completed_filename = f"{base_name}_completed_{timestamp}.docx"
        completed_path = os.path.join(upload_folder, completed_filename)
        
        # Replace placeholders
        logger.info(f"Replacing placeholders in document: {filename}")
        logger.debug(f"Answers provided: {len(answers)} placeholders")
        
        replace_placeholders(input_path, completed_path, answers)
        
        # Generate HTML preview
        logger.info("Generating HTML preview")
        html_preview = generate_preview_html(completed_path)
        
        # Store preview HTML in session (for serving later)
        session['preview_html'] = html_preview
        session['completed_filename'] = completed_filename
        session['completed_path'] = completed_path
        session.modified = True
        
        logger.info(f"Preview generated successfully: {completed_filename}")
        
        return jsonify({
            'success': True,
            'message': 'Preview generated successfully',
            'filename': completed_filename,
            'total_replacements': len(answers)
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except DocumentReplacementError as e:
        logger.error(f"Document replacement error: {e}")
        return handle_api_error(e, 'Failed to process document')
    except PreviewGenerationError as e:
        logger.error(f"Preview generation error: {e}")
        return handle_api_error(e, 'Failed to generate preview')
    except Exception as e:
        logger.error(f"Unexpected error generating preview: {e}")
        return handle_api_error(e, 'Failed to generate preview')


@preview_bp.route('/api/preview/html', methods=['GET'])
def get_preview_html():
    """
    Serve the HTML preview content.
    
    Returns:
        HTML content as text/html
    """
    try:
        # Retrieve preview HTML from session
        html_content = session.get('preview_html')
        
        if not html_content:
            raise SessionExpiredError('No preview available. Please generate preview first.')
        
        logger.info("Serving HTML preview")
        
        # Return HTML content directly
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error serving preview HTML: {e}")
        return handle_api_error(e, 'Failed to serve preview')


@preview_bp.route('/api/preview/status', methods=['GET'])
def get_preview_status():
    """
    Check if a preview is available in the session.
    
    Returns:
        JSON with preview availability status
    """
    try:
        has_preview = 'preview_html' in session and 'completed_filename' in session
        completed_filename = session.get('completed_filename')
        
        return jsonify({
            'success': True,
            'has_preview': has_preview,
            'filename': completed_filename if has_preview else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking preview status: {e}")
        return handle_api_error(e, 'Failed to check preview status')


@preview_bp.route('/api/preview/regenerate', methods=['POST'])
def regenerate_preview():
    """
    Regenerate the preview (useful after editing answers).
    Same as generate but explicitly for regeneration.
    
    Returns:
        JSON with success status
    """
    try:
        # Clear existing preview
        if 'preview_html' in session:
            session.pop('preview_html')
        if 'completed_path' in session:
            # Clean up old completed file
            old_path = session.get('completed_path')
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    logger.info(f"Removed old completed file: {old_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up old file: {cleanup_error}")
            session.pop('completed_path')
        if 'completed_filename' in session:
            session.pop('completed_filename')
        
        session.modified = True
        
        # Generate new preview
        return generate_preview()
        
    except Exception as e:
        logger.error(f"Error regenerating preview: {e}")
        return handle_api_error(e, 'Failed to regenerate preview')


@preview_bp.route('/api/preview/clear', methods=['POST'])
def clear_preview():
    """
    Clear the preview from session and clean up files.
    
    Returns:
        JSON with success status
    """
    try:
        # Clean up completed file if exists
        completed_path = session.get('completed_path')
        if completed_path and os.path.exists(completed_path):
            try:
                os.remove(completed_path)
                logger.info(f"Removed completed file: {completed_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up completed file: {cleanup_error}")
        
        # Clear preview data from session
        if 'preview_html' in session:
            session.pop('preview_html')
        if 'completed_path' in session:
            session.pop('completed_path')
        if 'completed_filename' in session:
            session.pop('completed_filename')
        
        session.modified = True
        
        logger.info("Preview cleared from session")
        
        return jsonify({
            'success': True,
            'message': 'Preview cleared successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing preview: {e}")
        return handle_api_error(e, 'Failed to clear preview')

