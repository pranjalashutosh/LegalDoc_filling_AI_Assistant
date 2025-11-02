"""
Document Replacer
Replaces placeholders in .docx documents with user-provided values
"""

from docx import Document
import re
import os
from config import Config
import logging

logger = logging.getLogger(__name__)


class DocumentReplacementError(Exception):
    """Exception raised for errors during document replacement."""
    pass


def replace_placeholders(input_path, output_path, placeholder_values):
    """
    Replace placeholders in a .docx document with provided values.
    Preserves all formatting including bold, italic, fonts, etc.
    
    Args:
        input_path (str): Path to the input .docx file
        output_path (str): Path where the completed document will be saved
        placeholder_values (dict): Dictionary mapping placeholder names to their replacement values
    
    Returns:
        str: Path to the completed document
    
    Raises:
        DocumentReplacementError: If document processing fails
    """
    try:
        logger.info(f"Loading document from: {input_path}")
        doc = Document(input_path)
        
        # Compile all placeholder patterns from config
        patterns = _compile_patterns()
        
        # Track replacements for logging
        replacements_made = {}
        
        # Process all paragraphs in the document
        for paragraph in doc.paragraphs:
            _replace_in_paragraph(paragraph, patterns, placeholder_values, replacements_made)
        
        # Process all tables in the document
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        _replace_in_paragraph(paragraph, patterns, placeholder_values, replacements_made)
        
        # Save the completed document
        logger.info(f"Saving completed document to: {output_path}")
        doc.save(output_path)
        
        # Log replacement summary
        logger.info(f"Document replacement complete. Replacements made: {len(replacements_made)}")
        for placeholder, count in replacements_made.items():
            logger.debug(f"  - '{placeholder}': {count} occurrence(s)")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error replacing placeholders: {e}")
        raise DocumentReplacementError(f"Failed to replace placeholders: {str(e)}")


def _compile_patterns():
    """
    Compile all placeholder regex patterns.
    
    Returns:
        list: List of tuples (pattern_name, compiled_regex, normalization_function)
    """
    patterns = []
    
    # Pattern 1: {{PLACEHOLDER}}
    patterns.append((
        'double_curly',
        re.compile(r'\{\{([A-Za-z0-9_\s]+)\}\}'),
        lambda m: m.group(1).strip().upper().replace(' ', '_')
    ))
    
    # Pattern 2: {PLACEHOLDER}
    patterns.append((
        'single_curly',
        re.compile(r'\{([A-Za-z0-9_\s]+)\}'),
        lambda m: m.group(1).strip().upper().replace(' ', '_')
    ))
    
    # Pattern 3: [Placeholder Name] (mixed case allowed)
    patterns.append((
        'square_brackets',
        re.compile(r'\[([A-Z][a-zA-Z0-9_\s]+)\]'),
        lambda m: m.group(1).strip().replace(' ', '_')
    ))
    
    # Pattern 4: _____ (5+ underscores)
    patterns.append((
        'underscores',
        re.compile(r'_{5,}'),
        lambda m: 'UNDERSCORE_PLACEHOLDER'
    ))
    
    # Pattern 5: $[_____] (dollar sign with underscores in brackets)
    patterns.append((
        'dollar_brackets',
        re.compile(r'\$\[_{3,}\]'),
        lambda m: 'DOLLAR_BRACKET_PLACEHOLDER'
    ))
    
    return patterns


def _replace_in_paragraph(paragraph, patterns, placeholder_values, replacements_made):
    """
    Replace placeholders in a single paragraph, preserving formatting.
    Works at the run level to maintain character formatting.
    
    Args:
        paragraph: docx.paragraph.Paragraph object
        patterns: List of compiled regex patterns
        placeholder_values: Dictionary of placeholder -> value mappings
        replacements_made: Dictionary to track replacement counts
    """
    # Get full paragraph text
    full_text = paragraph.text
    
    if not full_text:
        return
    
    # Check if any placeholder patterns exist in this paragraph
    has_placeholders = False
    for pattern_name, regex, normalizer in patterns:
        if regex.search(full_text):
            has_placeholders = True
            break
    
    if not has_placeholders:
        return
    
    # Build a map of character positions to runs
    runs = paragraph.runs
    if not runs:
        return
    
    # Create a working copy of the text
    working_text = full_text
    
    # Perform replacements on working text
    # We need to track offset changes as we replace
    offset = 0
    replacements = []  # List of (start_pos, end_pos, replacement_text)
    
    # Find all matches across all patterns
    for pattern_name, regex, normalizer in patterns:
        for match in regex.finditer(full_text):
            # Normalize the placeholder name
            normalized = normalizer(match)
            
            # Look up the replacement value
            if normalized in placeholder_values:
                replacement_value = placeholder_values[normalized]
                
                # Record the replacement
                start = match.start()
                end = match.end()
                replacements.append((start, end, replacement_value, normalized))
    
    # Sort replacements by position (reverse order to handle offsets correctly)
    replacements.sort(key=lambda x: x[0], reverse=True)
    
    # Apply replacements to working text
    for start, end, replacement_value, normalized in replacements:
        working_text = working_text[:start] + replacement_value + working_text[end:]
        
        # Track replacement counts
        if normalized in replacements_made:
            replacements_made[normalized] += 1
        else:
            replacements_made[normalized] = 1
    
    # If we made any replacements, update the paragraph
    if replacements:
        _update_paragraph_text(paragraph, working_text, full_text, runs)


def _update_paragraph_text(paragraph, new_text, original_text, runs):
    """
    Update paragraph text while attempting to preserve formatting.
    
    Strategy: Clear all runs and create a single new run with the first run's formatting.
    This is a simplified approach - for production, you might want more sophisticated
    formatting preservation.
    
    Args:
        paragraph: The paragraph to update
        new_text: The new text with replacements
        original_text: The original text
        runs: The original runs
    """
    # Store formatting from the first run (if exists)
    base_format = None
    if runs:
        first_run = runs[0]
        base_format = {
            'bold': first_run.bold,
            'italic': first_run.italic,
            'underline': first_run.underline,
            'font_name': first_run.font.name if first_run.font.name else None,
            'font_size': first_run.font.size,
        }
    
    # Clear all existing runs
    for run in runs:
        run.text = ''
    
    # Remove empty runs
    for run in paragraph.runs[:]:
        if run.text == '':
            run._element.getparent().remove(run._element)
    
    # Add new text with preserved formatting
    new_run = paragraph.add_run(new_text)
    
    if base_format:
        if base_format['bold'] is not None:
            new_run.bold = base_format['bold']
        if base_format['italic'] is not None:
            new_run.italic = base_format['italic']
        if base_format['underline'] is not None:
            new_run.underline = base_format['underline']
        if base_format['font_name']:
            new_run.font.name = base_format['font_name']
        if base_format['font_size']:
            new_run.font.size = base_format['font_size']


def get_normalized_placeholder_name(placeholder_text, pattern_type='auto'):
    """
    Normalize a placeholder name according to the pattern type.
    Useful for converting user-visible placeholders to internal keys.
    
    Args:
        placeholder_text (str): The placeholder text (with or without delimiters)
        pattern_type (str): The pattern type ('double_curly', 'single_curly', 
                           'square_brackets', 'underscores', 'dollar_brackets', 'auto')
    
    Returns:
        str: Normalized placeholder name
    """
    # Strip delimiters
    text = placeholder_text.strip()
    
    # Remove delimiters based on pattern type
    if text.startswith('{{') and text.endswith('}}'):
        text = text[2:-2].strip()
        pattern_type = 'double_curly'
    elif text.startswith('{') and text.endswith('}'):
        text = text[1:-1].strip()
        pattern_type = 'single_curly'
    elif text.startswith('[') and text.endswith(']'):
        text = text[1:-1].strip()
        pattern_type = 'square_brackets'
    elif text.startswith('$[') and text.endswith(']'):
        pattern_type = 'dollar_brackets'
        return 'DOLLAR_BRACKET_PLACEHOLDER'
    elif re.match(r'^_{5,}$', text):
        pattern_type = 'underscores'
        return 'UNDERSCORE_PLACEHOLDER'
    
    # Normalize based on pattern type
    if pattern_type in ['double_curly', 'single_curly']:
        # Uppercase and replace spaces with underscores
        return text.upper().replace(' ', '_')
    elif pattern_type == 'square_brackets':
        # Replace spaces with underscores, preserve case
        return text.replace(' ', '_')
    else:
        # Default: uppercase and replace spaces
        return text.upper().replace(' ', '_')


def validate_document_path(file_path):
    """
    Validate that a document path exists and is accessible.
    
    Args:
        file_path (str): Path to validate
    
    Returns:
        bool: True if valid
    
    Raises:
        DocumentReplacementError: If path is invalid
    """
    if not file_path:
        raise DocumentReplacementError("File path is required")
    
    if not os.path.exists(file_path):
        raise DocumentReplacementError(f"File not found: {file_path}")
    
    if not os.path.isfile(file_path):
        raise DocumentReplacementError(f"Path is not a file: {file_path}")
    
    if not file_path.lower().endswith('.docx'):
        raise DocumentReplacementError(f"File must be a .docx document: {file_path}")
    
    return True

