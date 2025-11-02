"""
LLM service for Legal Document Filler using Google Gemini 2.5 Pro.
Generates natural language questions for placeholder fields.
"""

import google.generativeai as genai
import os
from functools import lru_cache
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
ENABLE_LLM = os.getenv('ENABLE_LLM', 'true').lower() == 'true'

# Model configuration
MODEL_NAME = 'gemini-2.0-flash-exp'  # Using Gemini 2.0 Flash for faster responses
GENERATION_CONFIG = {
    'temperature': 0.3,  # More consistent, less creative
    'max_output_tokens': 100,
    'top_p': 0.8,
}

# Rate limiting tracking
_rate_limit_tracker = {
    'requests': [],
    'max_per_minute': 15  # Gemini free tier: 15 RPM
}


def initialize_gemini():
    """
    Initialize the Gemini API with the API key.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global GOOGLE_API_KEY, ENABLE_LLM
    
    if not ENABLE_LLM:
        logger.info("LLM is disabled via ENABLE_LLM environment variable")
        return False
    
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not found. LLM features will be disabled.")
        return False
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        logger.info(f"Gemini API initialized successfully with model: {MODEL_NAME}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {str(e)}")
        return False


def get_model():
    """
    Get the configured Gemini model instance.
    
    Returns:
        GenerativeModel: Configured model instance or None if not available
    """
    if not initialize_gemini():
        return None
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        return model
    except Exception as e:
        logger.error(f"Failed to create model instance: {str(e)}")
        return None


def check_rate_limit():
    """
    Check if we're within rate limits.
    
    Returns:
        tuple: (allowed: bool, wait_seconds: int)
    """
    global _rate_limit_tracker
    
    now = datetime.now()
    one_minute_ago = now - timedelta(minutes=1)
    
    # Remove requests older than 1 minute
    _rate_limit_tracker['requests'] = [
        req_time for req_time in _rate_limit_tracker['requests']
        if req_time > one_minute_ago
    ]
    
    current_count = len(_rate_limit_tracker['requests'])
    max_requests = _rate_limit_tracker['max_per_minute']
    
    if current_count >= max_requests:
        # Calculate wait time
        oldest_request = min(_rate_limit_tracker['requests'])
        wait_seconds = int((oldest_request + timedelta(minutes=1) - now).total_seconds()) + 1
        return False, wait_seconds
    
    return True, 0


def record_request():
    """Record a new API request for rate limiting."""
    _rate_limit_tracker['requests'].append(datetime.now())


def is_llm_enabled():
    """
    Check if LLM is enabled and available.
    
    Returns:
        bool: True if LLM can be used
    """
    return ENABLE_LLM and GOOGLE_API_KEY is not None


# Initialize on module load
_gemini_initialized = initialize_gemini()


@lru_cache(maxsize=100)
def generate_question(placeholder_name: str, use_llm: bool = True) -> str:
    """
    Generate a natural language question for a placeholder using Gemini 2.0 Flash.
    
    Uses LRU cache to avoid repeated API calls for the same placeholder.
    
    Args:
        placeholder_name (str): The normalized placeholder name (e.g., 'client_name')
        use_llm (bool): Whether to use LLM or return fallback directly
    
    Returns:
        str: Generated question or fallback question
    
    Examples:
        >>> generate_question('client_name')
        'What is the client's full legal name?'
        
        >>> generate_question('signing_date')
        'When will this document be signed? (Please provide a date)'
    """
    # Fallback question
    formatted_name = placeholder_name.replace('_', ' ').title()
    fallback = f"Please provide: {formatted_name}"
    
    # Check if LLM should be used
    if not use_llm or not is_llm_enabled():
        logger.debug(f"LLM disabled, using fallback for: {placeholder_name}")
        return fallback
    
    # Check rate limits
    allowed, wait_seconds = check_rate_limit()
    if not allowed:
        logger.warning(f"Rate limit exceeded. Wait {wait_seconds}s. Using fallback.")
        return fallback
    
    try:
        # Get model
        model = get_model()
        if not model:
            logger.warning("Model not available, using fallback")
            return fallback
        
        # Create prompt
        prompt = f"""Convert this placeholder name into a clear, professional question for a legal document.

The question should:
- Be concise (one sentence)
- Be professional and formal in tone
- Clearly indicate what information is needed
- Be suitable for a legal document context

Placeholder name: {placeholder_name}

Generate only the question, nothing else:"""
        
        # Record request for rate limiting
        record_request()
        
        # Generate content with timeout
        try:
            response = model.generate_content(
                prompt,
                generation_config=GENERATION_CONFIG,
                request_options={'timeout': 3}
            )
            
            # Extract text
            if response and hasattr(response, 'text'):
                question = response.text.strip()
                
                # Clean up response
                # Remove quotes if present
                question = question.strip('"\'')
                
                # Ensure it ends with proper punctuation
                if question and not question.endswith(('?', '.', '!')):
                    question += '?'
                
                # Validate question is reasonable length
                if len(question) > 0 and len(question) <= 500:
                    logger.info(f"Generated question for '{placeholder_name}': {question}")
                    return question
                else:
                    logger.warning(f"Generated question invalid length: {len(question)}")
                    return fallback
            else:
                logger.warning("No text in response, using fallback")
                return fallback
                
        except TimeoutError:
            logger.warning(f"Timeout generating question for '{placeholder_name}'")
            return fallback
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return fallback
    
    except Exception as e:
        logger.error(f"Unexpected error in generate_question: {str(e)}")
        return fallback


def generate_questions_batch(placeholder_names: list) -> dict:
    """
    Generate questions for multiple placeholders in a single API call.
    More efficient than individual calls when you have many placeholders.
    
    Args:
        placeholder_names (list): List of normalized placeholder names
    
    Returns:
        dict: {placeholder_name: question} for all placeholders
    
    Example:
        >>> generate_questions_batch(['client_name', 'signing_date', 'amount'])
        {
            'client_name': 'What is the client's full legal name?',
            'signing_date': 'When will this document be signed?',
            'amount': 'What is the total amount?'
        }
    """
    if not placeholder_names:
        return {}
    
    # Check if LLM is enabled
    if not is_llm_enabled():
        logger.debug("LLM disabled, using fallback for batch")
        return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                for name in placeholder_names}
    
    # Check rate limits
    allowed, wait_seconds = check_rate_limit()
    if not allowed:
        logger.warning(f"Rate limit exceeded. Using fallback for batch.")
        return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                for name in placeholder_names}
    
    try:
        # Get model
        model = get_model()
        if not model:
            logger.warning("Model not available, using fallback for batch")
            return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                    for name in placeholder_names}
        
        # Create numbered list of placeholders
        placeholders_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(placeholder_names)])
        
        # Create batch prompt
        prompt = f"""Convert these placeholder names into clear, professional questions for a legal document.

Instructions:
- Generate one question per placeholder
- Keep questions concise (one sentence each)
- Use professional and formal tone
- Clearly indicate what information is needed
- Number each question to match the placeholder number
- Format: "1. [question]" for each line

Placeholders:
{placeholders_list}

Generate the questions (numbered 1-{len(placeholder_names)}):"""
        
        # Record request for rate limiting
        record_request()
        
        # Generate content with timeout
        try:
            response = model.generate_content(
                prompt,
                generation_config=GENERATION_CONFIG,
                request_options={'timeout': 5}  # Slightly longer timeout for batch
            )
            
            # Parse response
            if response and hasattr(response, 'text'):
                response_text = response.text.strip()
                lines = response_text.split('\n')
                
                questions = {}
                
                # Parse each line
                for i, name in enumerate(placeholder_names):
                    question_number = i + 1
                    found = False
                    
                    # Look for the numbered question
                    for line in lines:
                        line = line.strip()
                        # Match patterns like "1.", "1)", "1:", "1 -", etc.
                        if line.startswith(f"{question_number}.") or \
                           line.startswith(f"{question_number})") or \
                           line.startswith(f"{question_number}:") or \
                           line.startswith(f"{question_number} -"):
                            # Extract question text
                            question = line.split(maxsplit=1)
                            if len(question) > 1:
                                question_text = question[1].strip()
                                # Clean up
                                question_text = question_text.strip('"\'')
                                if question_text and not question_text.endswith(('?', '.', '!')):
                                    question_text += '?'
                                
                                if len(question_text) > 0 and len(question_text) <= 500:
                                    questions[name] = question_text
                                    found = True
                                    break
                    
                    # Fallback for this placeholder if not found or invalid
                    if not found:
                        questions[name] = f"Please provide: {name.replace('_', ' ').title()}"
                
                logger.info(f"Generated {len(questions)} questions in batch (success: {sum(1 for q in questions.values() if 'Please provide' not in q)})")
                return questions
            
            else:
                logger.warning("No text in batch response, using fallback")
                return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                        for name in placeholder_names}
        
        except TimeoutError:
            logger.warning("Timeout in batch generation, using fallback")
            return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                    for name in placeholder_names}
        except Exception as e:
            logger.error(f"Error in batch API call: {str(e)}")
            return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                    for name in placeholder_names}
    
    except Exception as e:
        logger.error(f"Unexpected error in batch generation: {str(e)}")
        return {name: f"Please provide: {name.replace('_', ' ').title()}" 
                for name in placeholder_names}


def clear_question_cache():
    """
    Clear the LRU cache for generated questions.
    Useful for testing or if you want fresh questions.
    """
    generate_question.cache_clear()
    logger.info("Question cache cleared")


def get_cache_info():
    """
    Get information about the question cache.
    
    Returns:
        dict: Cache statistics (hits, misses, size, maxsize)
    """
    cache_info = generate_question.cache_info()
    return {
        'hits': cache_info.hits,
        'misses': cache_info.misses,
        'size': cache_info.currsize,
        'maxsize': cache_info.maxsize
    }


