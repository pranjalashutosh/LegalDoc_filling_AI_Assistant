"""
Placeholder detection routes for Legal Document Filler.
Handles detection of placeholders in uploaded documents.
"""

from flask import Blueprint, request, jsonify, session, current_app
from lib.placeholder_detector import (
    detect_placeholders,
    reduce_false_positives,
    get_placeholder_summary,
    PlaceholderDetectionError
)
from lib.error_handlers import (
    handle_docx_error,
    validate_docx_file,
    get_error_response
)
import os
from datetime import datetime

# Create blueprint
detect_bp = Blueprint('detect', __name__)


@detect_bp.route('/detect', methods=['POST'])
def detect():
    """
    Detect placeholders in the uploaded document.
    
    Returns:
        JSON response with detected placeholders and counts
    """
    try:
        # Check if file has been uploaded
        if 'uploaded_file' not in session:
            return jsonify({
                'success': False,
                'error': 'No file uploaded',
                'message': 'Please upload a .docx file before detecting placeholders.'
            }), 400
        
        file_info = session['uploaded_file']
        file_path = file_info.get('file_path')
        
        # Verify file exists
        if not file_path or not os.path.exists(file_path):
            return get_error_response('file_not_found', 404)
        
        # Validate docx file structure
        is_valid, error_response = validate_docx_file(file_path)
        if not is_valid:
            return error_response
        
        # Detect placeholders
        try:
            raw_placeholders = detect_placeholders(file_path)
        except PlaceholderDetectionError as e:
            return handle_docx_error(e, current_app.logger)
        except Exception as e:
            return handle_docx_error(e, current_app.logger)
        
        # Apply false positive filtering
        filtered_placeholders = reduce_false_positives(raw_placeholders)
        
        # Check if any placeholders were found after filtering
        if not filtered_placeholders or len(filtered_placeholders) == 0:
            return get_error_response('no_placeholders', 200, {
                'raw_detected': len(raw_placeholders),
                'note': 'Some patterns were detected but filtered out as false positives (e.g., citations, section references)'
            })
        
        # Get summary
        summary = get_placeholder_summary(filtered_placeholders)
        
        # Store in session
        session['placeholders'] = {
            'raw': raw_placeholders,
            'filtered': filtered_placeholders,
            'summary': summary,
            'detected_at': datetime.utcnow().isoformat()
        }
        
        # Update last activity
        session['last_activity'] = datetime.utcnow().isoformat()
        
        # Log detection for debugging
        current_app.logger.info(
            f"Detected {summary['total_unique']} unique placeholders "
            f"({summary['total_occurrences']} occurrences) in {file_info.get('original_filename')}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Placeholders detected successfully',
            'placeholders': filtered_placeholders,
            'summary': {
                'total_unique': summary['total_unique'],
                'total_occurrences': summary['total_occurrences'],
                'placeholder_names': summary['placeholders'],
                'counts': summary['counts']
            },
            'grouped': summary['grouped'],
            'detected_at': session['placeholders']['detected_at']
        }), 200
    
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"Detection error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Detection failed',
            'message': 'An unexpected error occurred during placeholder detection.'
        }), 500


@detect_bp.route('/detect/status', methods=['GET'])
def detect_status():
    """
    Check detection status for current session.
    
    Returns:
        JSON response with detection status
    """
    try:
        if 'placeholders' not in session:
            return jsonify({
                'success': True,
                'detected': False,
                'message': 'No placeholders detected yet'
            }), 200
        
        placeholder_info = session['placeholders']
        summary = placeholder_info.get('summary', {})
        
        return jsonify({
            'success': True,
            'detected': True,
            'total_unique': summary.get('total_unique', 0),
            'total_occurrences': summary.get('total_occurrences', 0),
            'detected_at': placeholder_info.get('detected_at')
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Status check error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Status check failed',
            'message': 'Unable to check detection status'
        }), 500


@detect_bp.route('/detect/details', methods=['GET'])
def detect_details():
    """
    Get detailed information about detected placeholders.
    
    Returns:
        JSON response with full placeholder details
    """
    try:
        if 'placeholders' not in session:
            return jsonify({
                'success': False,
                'error': 'Not detected',
                'message': 'No placeholders have been detected yet'
            }), 404
        
        placeholder_info = session['placeholders']
        summary = placeholder_info.get('summary', {})
        
        return jsonify({
            'success': True,
            'placeholders': placeholder_info.get('filtered', {}),
            'summary': summary,
            'raw_count': len(placeholder_info.get('raw', {})),
            'filtered_count': len(placeholder_info.get('filtered', {})),
            'detected_at': placeholder_info.get('detected_at')
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Details retrieval error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Retrieval failed',
            'message': 'Unable to retrieve placeholder details'
        }), 500


@detect_bp.route('/detect/redetect', methods=['POST'])
def redetect():
    """
    Re-run placeholder detection (useful if file was replaced).
    
    Returns:
        JSON response with new detection results
    """
    try:
        # Clear existing detection data
        if 'placeholders' in session:
            session.pop('placeholders', None)
        
        # Run detection again
        return detect()
    
    except Exception as e:
        current_app.logger.error(f"Re-detection error: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Re-detection failed',
            'message': 'Unable to re-detect placeholders'
        }), 500

