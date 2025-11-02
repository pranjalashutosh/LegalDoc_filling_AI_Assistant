"""
Preview Generator
Converts .docx documents to HTML for in-browser preview
"""

import mammoth
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PreviewGenerationError(Exception):
    """Exception raised for errors during preview generation."""
    pass


def generate_preview_html(docx_path):
    """
    Convert a .docx document to HTML for preview.
    
    Args:
        docx_path (str): Path to the .docx file
    
    Returns:
        str: Complete HTML string with styling
    
    Raises:
        PreviewGenerationError: If conversion fails
    """
    try:
        logger.info(f"Generating HTML preview for: {docx_path}")
        
        # Validate file exists
        if not os.path.exists(docx_path):
            raise PreviewGenerationError(f"File not found: {docx_path}")
        
        # Convert .docx to HTML using mammoth
        with open(docx_path, 'rb') as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html_content = result.value  # The generated HTML
            messages = result.messages  # Any messages (warnings, errors)
        
        # Log any warnings or messages
        if messages:
            for message in messages:
                logger.warning(f"Mammoth message: {message}")
        
        # Wrap the HTML content in a styled template
        styled_html = _wrap_in_template(html_content)
        
        logger.info("HTML preview generated successfully")
        return styled_html
        
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise PreviewGenerationError(f"Failed to generate preview: {str(e)}")


def generate_preview_html_from_bytes(docx_bytes):
    """
    Convert .docx file bytes to HTML for preview.
    Useful when working with in-memory files.
    
    Args:
        docx_bytes (bytes): The .docx file content as bytes
    
    Returns:
        str: Complete HTML string with styling
    
    Raises:
        PreviewGenerationError: If conversion fails
    """
    try:
        logger.info("Generating HTML preview from bytes")
        
        # Convert .docx bytes to HTML using mammoth
        result = mammoth.convert_to_html(docx_bytes)
        html_content = result.value
        messages = result.messages
        
        # Log any warnings or messages
        if messages:
            for message in messages:
                logger.warning(f"Mammoth message: {message}")
        
        # Wrap the HTML content in a styled template
        styled_html = _wrap_in_template(html_content)
        
        logger.info("HTML preview generated successfully from bytes")
        return styled_html
        
    except Exception as e:
        logger.error(f"Error generating preview from bytes: {e}")
        raise PreviewGenerationError(f"Failed to generate preview: {str(e)}")


def _wrap_in_template(html_content):
    """
    Wrap the converted HTML in a complete HTML document with styling.
    
    Args:
        html_content (str): The HTML content from mammoth conversion
    
    Returns:
        str: Complete HTML document with styling
    """
    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Calibri', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #000000;
            background-color: #ffffff;
            padding: 2rem;
            max-width: 8.5in;
            margin: 0 auto;
        }}
        
        /* Headings */
        h1 {{
            font-size: 16pt;
            font-weight: bold;
            margin: 1.5rem 0 1rem 0;
            color: #000000;
        }}
        
        h2 {{
            font-size: 14pt;
            font-weight: bold;
            margin: 1.25rem 0 0.75rem 0;
            color: #000000;
        }}
        
        h3 {{
            font-size: 12pt;
            font-weight: bold;
            margin: 1rem 0 0.5rem 0;
            color: #000000;
        }}
        
        /* Paragraphs */
        p {{
            margin-bottom: 0.5rem;
            text-align: justify;
        }}
        
        /* Lists */
        ul, ol {{
            margin: 0.5rem 0 0.5rem 2rem;
        }}
        
        li {{
            margin-bottom: 0.25rem;
        }}
        
        /* Tables */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }}
        
        table, th, td {{
            border: 1px solid #000000;
        }}
        
        th, td {{
            padding: 0.5rem;
            text-align: left;
        }}
        
        th {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}
        
        /* Bold and Italic */
        strong, b {{
            font-weight: bold;
        }}
        
        em, i {{
            font-style: italic;
        }}
        
        /* Underline */
        u {{
            text-decoration: underline;
        }}
        
        /* Links */
        a {{
            color: #0563c1;
            text-decoration: underline;
        }}
        
        a:hover {{
            color: #0451a5;
        }}
        
        /* Blockquotes */
        blockquote {{
            margin: 1rem 0;
            padding-left: 1rem;
            border-left: 3px solid #cccccc;
            font-style: italic;
        }}
        
        /* Code */
        code {{
            font-family: 'Courier New', monospace;
            background-color: #f4f4f4;
            padding: 0.125rem 0.25rem;
            border-radius: 3px;
        }}
        
        pre {{
            font-family: 'Courier New', monospace;
            background-color: #f4f4f4;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            margin: 1rem 0;
        }}
        
        /* Horizontal Rule */
        hr {{
            border: none;
            border-top: 1px solid #cccccc;
            margin: 1.5rem 0;
        }}
        
        /* Responsive adjustments */
        @media (max-width: 768px) {{
            body {{
                padding: 1rem;
                font-size: 10pt;
            }}
        }}
        
        @media print {{
            body {{
                padding: 0;
                max-width: none;
            }}
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
    return template


def save_preview_html(html_content, output_path):
    """
    Save the generated HTML preview to a file.
    
    Args:
        html_content (str): The HTML content to save
        output_path (str): Path where the HTML file will be saved
    
    Returns:
        str: Path to the saved HTML file
    
    Raises:
        PreviewGenerationError: If saving fails
    """
    try:
        logger.info(f"Saving HTML preview to: {output_path}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write HTML to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info("HTML preview saved successfully")
        return output_path
        
    except Exception as e:
        logger.error(f"Error saving HTML preview: {e}")
        raise PreviewGenerationError(f"Failed to save preview: {str(e)}")


def validate_docx_file(file_path):
    """
    Validate that a file is a valid .docx document.
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        bool: True if valid
    
    Raises:
        PreviewGenerationError: If validation fails
    """
    if not file_path:
        raise PreviewGenerationError("File path is required")
    
    if not os.path.exists(file_path):
        raise PreviewGenerationError(f"File not found: {file_path}")
    
    if not os.path.isfile(file_path):
        raise PreviewGenerationError(f"Path is not a file: {file_path}")
    
    if not file_path.lower().endswith('.docx'):
        raise PreviewGenerationError(f"File must be a .docx document: {file_path}")
    
    # Try to open with mammoth to validate
    try:
        with open(file_path, 'rb') as f:
            # Just attempt to read the first few bytes
            f.read(8)
        return True
    except Exception as e:
        raise PreviewGenerationError(f"Invalid .docx file: {str(e)}")

