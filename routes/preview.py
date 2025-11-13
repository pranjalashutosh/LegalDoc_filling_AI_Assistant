"""
Preview API Routes
Handles document preview generation and serving
"""

from flask import Blueprint, request, session, jsonify, send_file
from lib.document_replacer import replace_placeholders, DocumentReplacementError
from lib.preview_generator import generate_preview_html, save_preview_html, PreviewGenerationError
from lib.error_handlers import handle_api_error, SessionExpiredError
from config import Config
import logging
import os
from datetime import datetime
import tempfile

logger = logging.getLogger(__name__)

# Create blueprint
preview_bp = Blueprint('preview', __name__)


@preview_bp.route('/preview/generate', methods=['POST'])
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
        uploaded = session.get('uploaded_file')
        answers = session.get('answers', {})
        placeholders = session.get('placeholders', [])
        
        if not uploaded or not uploaded.get('file_path'):
            raise SessionExpiredError('No uploaded file found in session')
        
        if not answers:
            return jsonify({
                'success': False,
                'error': 'No answers provided. Please fill in at least one placeholder.'
            }), 400
        
        # Construct input file path
        # Use the exact saved file path from upload step
        input_path = uploaded['file_path']
        
        if not os.path.exists(input_path):
            raise SessionExpiredError('Uploaded file no longer exists. Please upload again.')
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name, _ = os.path.splitext(uploaded.get('safe_filename') or uploaded.get('original_filename') or 'document')
        completed_filename = f"{base_name}_completed_{timestamp}.docx"
        # Save the completed file in the same session-specific folder as the upload
        session_folder = os.path.dirname(input_path)
        completed_path = os.path.join(session_folder, completed_filename)
        
        # Replace placeholders
        logger.info(
            f"Replacing placeholders in document: {uploaded.get('original_filename') or uploaded.get('safe_filename')}"
        )
        logger.debug(f"Answers provided: {len(answers)} placeholders")
        
        # Include per-instance overrides if any
        overrides = session.get('answers_overrides', {})
        replace_placeholders(input_path, completed_path, answers, overrides)
        
        # Generate HTML preview and save to file (avoid storing large HTML in session cookie)
        logger.info("Generating HTML preview")
        html_preview = generate_preview_html(completed_path)

        # Persist preview to an .html file in the same session folder
        preview_filename = f"{base_name}_preview_{timestamp}.html"
        preview_path = os.path.join(session_folder, preview_filename)
        save_preview_html(html_preview, preview_path)

        # Store only file paths and filenames in session (small cookie size)
        session['preview_html_path'] = preview_path
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


@preview_bp.route('/preview/html', methods=['GET'])
def get_preview_html():
    """
    Serve the HTML preview content.
    
    Returns:
        HTML content as text/html
    """
    try:
        # Prefer reading from saved preview file
        preview_path = session.get('preview_html_path')
        completed_path = session.get('completed_path')

        # If preview file exists, serve it
        if preview_path and os.path.exists(preview_path):
            logger.info("Serving HTML preview from file")
            with open(preview_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            from flask import Response
            return Response(html_content, mimetype='text/html')

        # If preview file missing but completed document exists, regenerate on the fly
        if completed_path and os.path.exists(completed_path):
            logger.info("Preview file missing; regenerating from completed document")
            html_content = generate_preview_html(completed_path)
            from flask import Response
            return Response(html_content, mimetype='text/html')

        # Otherwise, no preview available
        raise SessionExpiredError('No preview available. Please generate preview first.')
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error serving preview HTML: {e}")
        return handle_api_error(e, 'Failed to serve preview')


@preview_bp.route('/preview/status', methods=['GET'])
def get_preview_status():
    """
    Check if a preview is available in the session.
    
    Returns:
        JSON with preview availability status
    """
    try:
        preview_path = session.get('preview_html_path')
        completed_path = session.get('completed_path')
        has_preview = bool(preview_path and os.path.exists(preview_path)) or bool(completed_path and os.path.exists(completed_path))
        completed_filename = session.get('completed_filename')
        
        return jsonify({
            'success': True,
            'has_preview': has_preview,
            'filename': completed_filename if has_preview else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking preview status: {e}")
        return handle_api_error(e, 'Failed to check preview status')


@preview_bp.route('/preview/regenerate', methods=['POST'])
def regenerate_preview():
    """
    Regenerate the preview (useful after editing answers).
    Same as generate but explicitly for regeneration.
    
    Returns:
        JSON with success status
    """
    try:
        # Clear existing preview
        preview_path = session.get('preview_html_path')
        if preview_path and os.path.exists(preview_path):
            try:
                os.remove(preview_path)
                logger.info(f"Removed preview file: {preview_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up preview file: {cleanup_error}")
        if 'preview_html_path' in session:
            session.pop('preview_html_path')
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


@preview_bp.route('/preview/clear', methods=['POST'])
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
        
        # Clean up preview file if exists
        preview_path = session.get('preview_html_path')
        if preview_path and os.path.exists(preview_path):
            try:
                os.remove(preview_path)
                logger.info(f"Removed preview file: {preview_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up preview file: {cleanup_error}")

        # Clear preview data from session
        if 'preview_html_path' in session:
            session.pop('preview_html_path')
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

