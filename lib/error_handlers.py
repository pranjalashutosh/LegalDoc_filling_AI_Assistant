"""
Error handling utilities for Legal Document Filler.
Provides custom error classes and user-friendly error messages.
"""

from flask import jsonify
import logging


# Custom exception classes
class FileValidationError(Exception):
    """Exception raised for file validation errors."""
    pass


class ParsingError(Exception):
    """Exception raised for document parsing errors."""
    pass


class LLMError(Exception):
    """Exception raised for LLM-related errors."""
    pass


class SessionExpiredError(Exception):
    """Exception raised when session has expired."""
    pass


# Error message mappings
ERROR_MESSAGES = {
    'file_not_found': {
        'title': 'File Not Found',
        'message': 'The uploaded file could not be found. Please upload your document again.',
        'suggestion': 'Make sure to upload a .docx file before proceeding.'
    },
    'invalid_docx': {
        'title': 'Invalid Document Format',
        'message': 'The file appears to be corrupted or is not a valid .docx file.',
        'suggestion': 'Please ensure you are uploading a Microsoft Word document (.docx format). If the file was created in an older version of Word, try re-saving it as a .docx file.'
    },
    'malformed_docx': {
        'title': 'Malformed Document',
        'message': 'The document structure is damaged and cannot be processed.',
        'suggestion': 'Try opening the document in Microsoft Word and saving a new copy, then upload the new file.'
    },
    'empty_document': {
        'title': 'Empty Document',
        'message': 'The document appears to be empty or contains no text.',
        'suggestion': 'Please upload a document that contains text with placeholders.'
    },
    'no_placeholders': {
        'title': 'No Placeholders Found',
        'message': 'No placeholders were detected in the document.',
        'suggestion': 'Make sure your document contains placeholders in one of these formats: {{name}}, {name}, [NAME], or _____ (underscores).'
    },
    'file_too_large': {
        'title': 'File Too Large',
        'message': 'The uploaded file exceeds the maximum allowed size.',
        'suggestion': 'Please upload a file smaller than 5 MB. Consider splitting large documents into smaller sections.'
    },
    'unsupported_format': {
        'title': 'Unsupported Format',
        'message': 'Only .docx files are supported.',
        'suggestion': 'If you have a .doc file, please convert it to .docx format using Microsoft Word or Google Docs.'
    },
    'session_expired': {
        'title': 'Session Expired',
        'message': 'Your session has expired due to inactivity.',
        'suggestion': 'Please start over by uploading your document again.'
    },
    'parsing_failed': {
        'title': 'Processing Failed',
        'message': 'An error occurred while processing your document.',
        'suggestion': 'This might be due to complex formatting or embedded objects. Try simplifying the document or removing embedded objects.'
    }
}


def get_error_response(error_type, status_code=400, additional_info=None):
    """
    Generate a standardized error response.
    
    Args:
        error_type (str): Type of error from ERROR_MESSAGES
        status_code (int): HTTP status code
        additional_info (dict): Additional information to include in response
    
    Returns:
        tuple: (JSON response, status code)
    """
    error_info = ERROR_MESSAGES.get(error_type, {
        'title': 'Error',
        'message': 'An unexpected error occurred.',
        'suggestion': 'Please try again or contact support if the problem persists.'
    })
    
    response = {
        'success': False,
        'error': error_info['title'],
        'message': error_info['message'],
        'suggestion': error_info['suggestion']
    }
    
    if additional_info:
        response.update(additional_info)
    
    return jsonify(response), status_code


def handle_docx_error(error, logger=None):
    """
    Handle errors related to .docx file processing.
    
    Args:
        error (Exception): The exception that occurred
        logger (logging.Logger): Logger instance for error logging
    
    Returns:
        tuple: (JSON response, status code)
    """
    if logger:
        logger.error(f"DOCX processing error: {str(error)}", exc_info=True)
    
    error_str = str(error).lower()
    
    # Determine error type based on exception message
    if 'not a zip file' in error_str or 'bad magic number' in error_str:
        return get_error_response('invalid_docx', 400)
    
    elif 'no such file' in error_str or 'file not found' in error_str:
        return get_error_response('file_not_found', 404)
    
    elif 'corrupted' in error_str or 'damaged' in error_str:
        return get_error_response('malformed_docx', 400)
    
    elif 'empty' in error_str:
        return get_error_response('empty_document', 400)
    
    elif 'permission denied' in error_str:
        return get_error_response('parsing_failed', 500, {
            'details': 'File access permission error'
        })
    
    else:
        # Generic parsing error
        return get_error_response('parsing_failed', 400, {
            'details': 'Document structure could not be parsed'
        })


def validate_docx_file(file_path):
    """
    Validate that a file is a valid .docx file before processing.
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        tuple: (is_valid, error_response or None)
    """
    import os
    import zipfile
    
    # Check file exists
    if not os.path.exists(file_path):
        return False, get_error_response('file_not_found', 404)
    
    # Check file is not empty
    if os.path.getsize(file_path) == 0:
        return False, get_error_response('empty_document', 400)
    
    # Check if it's a valid ZIP file (docx is ZIP-based)
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            # Check for required docx structure
            required_files = ['[Content_Types].xml', 'word/document.xml']
            file_list = zip_file.namelist()
            
            for required in required_files:
                if required not in file_list:
                    return False, get_error_response('malformed_docx', 400)
        
        return True, None
    
    except zipfile.BadZipFile:
        return False, get_error_response('invalid_docx', 400)
    
    except Exception as e:
        return False, get_error_response('parsing_failed', 400, {
            'details': 'Could not validate document structure'
        })


# Flask error handler registration functions
def register_error_handlers(app):
    """
    Register custom error handlers with Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(FileValidationError)
    def handle_file_validation_error(error):
        """Handle file validation errors."""
        return jsonify({
            'success': False,
            'error': 'File Validation Error',
            'message': str(error)
        }), 400
    
    @app.errorhandler(ParsingError)
    def handle_parsing_error(error):
        """Handle document parsing errors."""
        return handle_docx_error(error, app.logger)
    
    @app.errorhandler(LLMError)
    def handle_llm_error(error):
        """Handle LLM-related errors."""
        app.logger.error(f"LLM error: {str(error)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'AI Service Error',
            'message': 'The AI service encountered an error. Using fallback mode.',
            'details': str(error)
        }), 500
    
    @app.errorhandler(SessionExpiredError)
    def handle_session_expired(error):
        """Handle session expiration."""
        return get_error_response('session_expired', 401)

