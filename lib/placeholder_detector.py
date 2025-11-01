"""
Placeholder detection for Legal Document Filler.
Detects multiple placeholder patterns in .docx files.
"""

import re
from docx import Document
from typing import Dict, List, Set


class PlaceholderDetectionError(Exception):
    """Custom exception for placeholder detection errors."""
    pass


def detect_placeholders(docx_path: str) -> Dict[str, List[str]]:
    """
    Detect placeholders in a .docx document using multiple patterns.
    
    Patterns supported:
    - {{placeholder_name}} - Double curly braces
    - {placeholder_name} - Single curly braces
    - [Placeholder Name] - Square brackets (any case, e.g., [Date of Safe])
    - _____ - Underscores (5 or more)
    - $[_____] - Dollar sign with brackets and underscores
    
    Args:
        docx_path (str): Path to the .docx file
    
    Returns:
        dict: {normalized_name: [original_patterns]}
              Example: {'client_name': ['{{client_name}}', '{CLIENT_NAME}']}
    
    Raises:
        PlaceholderDetectionError: If document cannot be parsed
    """
    try:
        doc = Document(docx_path)
    except Exception as e:
        raise PlaceholderDetectionError(f"Failed to open document: {str(e)}")
    
    placeholders = {}  # {normalized_name: [original_patterns]}
    
    # Define regex patterns
    patterns = [
        (r'\{\{([a-zA-Z0-9_]+)\}\}', 'double_curly'),           # {{name}}
        (r'\{([a-zA-Z0-9_]+)\}', 'single_curly'),               # {name}
        (r'\[([A-Z][a-zA-Z0-9_\s]+)\]', 'square_bracket'),      # [Date of Safe], [NAME]
        (r'_{5,}', 'underscore'),                               # _____
        (r'\$\[_{5,}\]', 'dollar_underscore'),                  # $[_____]
    ]
    
    # Track context for underscore patterns
    underscore_counter = 0
    
    # Parse document paragraphs
    for paragraph in doc.paragraphs:
        text = paragraph.text
        
        if not text.strip():
            continue
        
        # Check each pattern
        for pattern, pattern_type in patterns:
            matches = re.finditer(pattern, text)
            
            for match in matches:
                original = match.group(0)
                
                # Normalize placeholder name
                if pattern_type == 'underscore':
                    # Try to extract label before underscores
                    # Look for pattern like "Name: _____" or "Name:_____"
                    before_match = text[:match.start()].strip()
                    label_match = re.search(r'(\w+)\s*:\s*$', before_match)
                    
                    if label_match:
                        normalized = label_match.group(1).lower()
                    else:
                        # Use generic name with counter
                        underscore_counter += 1
                        normalized = f"field_{underscore_counter}"
                
                elif pattern_type == 'dollar_underscore':
                    # Try to find label or use generic name
                    before_match = text[:match.start()].strip()
                    label_match = re.search(r'(\w+)\s*$', before_match)
                    
                    if label_match:
                        normalized = label_match.group(1).lower()
                    else:
                        normalized = f"amount_{len([k for k in placeholders.keys() if k.startswith('amount_')]) + 1}"
                
                else:
                    # For other patterns, normalize the captured content
                    captured = match.group(1)
                    normalized = captured.lower().replace(' ', '_')
                
                # Add to placeholders dict
                if normalized not in placeholders:
                    placeholders[normalized] = []
                
                # Only add if not already in list (avoid duplicates in same paragraph)
                if original not in placeholders[normalized]:
                    placeholders[normalized].append(original)
    
    return placeholders


def reduce_false_positives(placeholders: Dict[str, List[str]], doc_text: str = None) -> Dict[str, List[str]]:
    """
    Filter out false positives from detected placeholders.
    
    Filters:
    - Numeric citations like [1], [2], [10]
    - Section references like [Section 2(b)], [2(a)]
    - Single-character brackets like [a], [x]
    - "section" keyword in placeholder names
    - Placeholders that appear only once and are very short (unless multi-word)
    
    Args:
        placeholders (dict): Result from detect_placeholders()
        doc_text (str): Full document text (optional, for additional context)
    
    Returns:
        dict: Filtered placeholders
    """
    filtered = {}
    
    for normalized, originals in placeholders.items():
        # Skip if normalized name is only digits
        if normalized.isdigit():
            continue
        
        # Skip if contains "section" keyword (likely a section reference)
        if 'section' in normalized.lower():
            continue
        
        # Skip if normalized name is a single character
        if len(normalized) == 1:
            continue
        
        # Check original patterns for false positive indicators
        has_false_positive = False
        
        for orig in originals:
            # Check if it's a square bracket pattern
            if orig.startswith('[') and orig.endswith(']'):
                content = orig[1:-1].strip()
                
                # Filter numeric citations: [1], [12], etc.
                if content.isdigit():
                    has_false_positive = True
                    break
                
                # Filter section references: [2(a)], [Section 2(b)], [Section 3]
                if re.match(r'^\d+\([a-z]\)$', content, re.IGNORECASE):
                    has_false_positive = True
                    break
                
                if re.match(r'^Section\s+\d+', content, re.IGNORECASE):
                    has_false_positive = True
                    break
                
                # Filter single character brackets: [a], [x]
                if len(content) == 1:
                    has_false_positive = True
                    break
        
        if has_false_positive:
            continue
        
        # Apply occurrence-based filtering
        occurrence_count = len(originals)
        
        # If appears only once, be more strict
        if occurrence_count == 1:
            # Keep if it's multi-word (has underscore in normalized name)
            if '_' not in normalized:
                # Skip single-occurrence, single-word placeholders that are very short
                if len(normalized) <= 3:
                    continue
        
        # If appears 2+ times or is multi-word, keep it
        if occurrence_count >= 2 or '_' in normalized or len(normalized) > 3:
            filtered[normalized] = originals
    
    return filtered


def get_placeholder_count(placeholders: Dict[str, List[str]]) -> Dict[str, int]:
    """
    Get count of occurrences for each placeholder.
    
    Args:
        placeholders (dict): Result from detect_placeholders()
    
    Returns:
        dict: {normalized_name: count}
    """
    return {name: len(originals) for name, originals in placeholders.items()}


def get_total_occurrences(placeholders: Dict[str, List[str]]) -> int:
    """
    Get total number of placeholder occurrences.
    
    Args:
        placeholders (dict): Result from detect_placeholders()
    
    Returns:
        int: Total occurrence count
    """
    return sum(len(originals) for originals in placeholders.values())


def normalize_placeholder_name(name: str) -> str:
    """
    Normalize a placeholder name to a consistent format.
    
    Rules:
    - Convert to lowercase
    - Replace spaces with underscores
    - Remove special characters except underscores
    
    Args:
        name (str): Original placeholder name
    
    Returns:
        str: Normalized name
    """
    # Convert to lowercase
    normalized = name.lower()
    
    # Replace spaces with underscores
    normalized = normalized.replace(' ', '_')
    
    # Remove special characters except underscores and alphanumeric
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    
    # Replace multiple underscores with single
    normalized = re.sub(r'_+', '_', normalized)
    
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


def group_similar_placeholders(placeholders: Dict[str, List[str]]) -> Dict[str, Dict[str, any]]:
    """
    Group placeholders with metadata.
    
    Args:
        placeholders (dict): Result from detect_placeholders()
    
    Returns:
        dict: Enhanced placeholder info with metadata
              {
                  'client_name': {
                      'normalized': 'client_name',
                      'variants': ['{{client_name}}', '{CLIENT_NAME}'],
                      'count': 2,
                      'patterns': ['double_curly', 'single_curly']
                  }
              }
    """
    grouped = {}
    
    for normalized, originals in placeholders.items():
        # Determine pattern types
        pattern_types = set()
        for orig in originals:
            if orig.startswith('{{') and orig.endswith('}}'):
                pattern_types.add('double_curly')
            elif orig.startswith('{') and orig.endswith('}'):
                pattern_types.add('single_curly')
            elif orig.startswith('[') and orig.endswith(']'):
                pattern_types.add('square_bracket')
            elif orig.startswith('$['):
                pattern_types.add('dollar_underscore')
            elif '_' in orig and not any(c.isalnum() for c in orig):
                pattern_types.add('underscore')
        
        grouped[normalized] = {
            'normalized': normalized,
            'variants': originals,
            'count': len(originals),
            'patterns': list(pattern_types)
        }
    
    return grouped


def get_placeholder_summary(placeholders: Dict[str, List[str]]) -> Dict[str, any]:
    """
    Get a summary of detected placeholders.
    
    Args:
        placeholders (dict): Result from detect_placeholders()
    
    Returns:
        dict: Summary with counts and statistics
    """
    total_unique = len(placeholders)
    total_occurrences = get_total_occurrences(placeholders)
    counts = get_placeholder_count(placeholders)
    grouped = group_similar_placeholders(placeholders)
    
    return {
        'total_unique': total_unique,
        'total_occurrences': total_occurrences,
        'placeholders': list(placeholders.keys()),
        'counts': counts,
        'grouped': grouped
    }

