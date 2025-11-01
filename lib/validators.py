"""
File validation utilities for Legal Document Filler.
Validates file extensions, sizes, and MIME types.
"""

import os
import mimetypes
from werkzeug.datastructures import FileStorage


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


def validate_file_extension(filename, allowed_extensions=None):
    """
    Validate that the file has an allowed extension.
    
    Args:
        filename (str): Name of the file to validate
        allowed_extensions (set): Set of allowed extensions (default: {'.docx'})
    
    Returns:
        bool: True if extension is valid
    
    Raises:
        FileValidationError: If extension is not allowed
    """
    if allowed_extensions is None:
        allowed_extensions = {'.docx'}
    
    if not filename:
        raise FileValidationError("No filename provided")
    
    # Get file extension (including the dot)
    _, ext = os.path.splitext(filename.lower())
    
    if not ext:
        raise FileValidationError("File has no extension")
    
    # Normalize allowed extensions to include dots
    normalized_extensions = set()
    for ext_item in allowed_extensions:
        if not ext_item.startswith('.'):
            normalized_extensions.add(f'.{ext_item}')
        else:
            normalized_extensions.add(ext_item)
    
    if ext not in normalized_extensions:
        allowed_list = ', '.join(sorted(normalized_extensions))
        raise FileValidationError(
            f"File type '{ext}' is not allowed. Allowed types: {allowed_list}"
        )
    
    return True


def validate_file_size(file_storage, max_size_bytes):
    """
    Validate that the file size is within allowed limits.
    
    Args:
        file_storage (FileStorage): Werkzeug FileStorage object
        max_size_bytes (int): Maximum allowed file size in bytes
    
    Returns:
        bool: True if size is valid
    
    Raises:
        FileValidationError: If file is too large
    """
    if not isinstance(file_storage, FileStorage):
        raise FileValidationError("Invalid file object")
    
    # Seek to end to get file size
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)  # Reset to beginning
    
    if file_size == 0:
        raise FileValidationError("File is empty")
    
    if file_size > max_size_bytes:
        max_size_mb = max_size_bytes / (1024 * 1024)
        actual_size_mb = file_size / (1024 * 1024)
        raise FileValidationError(
            f"File size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB)"
        )
    
    return True


def validate_mime_type(file_storage, allowed_mime_types=None):
    """
    Validate the MIME type of the file.
    
    Args:
        file_storage (FileStorage): Werkzeug FileStorage object
        allowed_mime_types (set): Set of allowed MIME types
    
    Returns:
        bool: True if MIME type is valid
    
    Raises:
        FileValidationError: If MIME type is not allowed
    """
    if allowed_mime_types is None:
        allowed_mime_types = {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
    
    if not isinstance(file_storage, FileStorage):
        raise FileValidationError("Invalid file object")
    
    # Get MIME type from filename
    filename = file_storage.filename
    mime_type, _ = mimetypes.guess_type(filename)
    
    # Also check the content_type from the upload
    content_type = file_storage.content_type
    
    # Validate against allowed types
    if mime_type not in allowed_mime_types and content_type not in allowed_mime_types:
        raise FileValidationError(
            f"File type is not supported. Only .docx files are allowed."
        )
    
    return True


def validate_file(file_storage, max_size_bytes, allowed_extensions=None):
    """
    Comprehensive file validation combining all checks.
    
    Args:
        file_storage (FileStorage): Werkzeug FileStorage object
        max_size_bytes (int): Maximum allowed file size in bytes
        allowed_extensions (set): Set of allowed extensions
    
    Returns:
        dict: Validation result with details
    
    Raises:
        FileValidationError: If any validation fails
    """
    if not file_storage or not file_storage.filename:
        raise FileValidationError("No file provided")
    
    filename = file_storage.filename
    
    # Run all validations
    validate_file_extension(filename, allowed_extensions)
    validate_file_size(file_storage, max_size_bytes)
    validate_mime_type(file_storage)
    
    # Get file size for response
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)
    
    return {
        'valid': True,
        'filename': filename,
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2)
    }


def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal and other security issues.
    
    Args:
        filename (str): Original filename
    
    Returns:
        str: Sanitized filename
    """
    if not filename:
        return 'unnamed_file'
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace potentially dangerous characters
    dangerous_chars = ['..', '/', '\\', '\0', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    
    return f"{name}{ext}"

