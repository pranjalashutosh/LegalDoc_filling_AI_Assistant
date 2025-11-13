"""
LLM service for Legal Document Filler using Google Gemini 2.5 Pro.
Generates natural language questions for placeholder fields.
"""

import google.generativeai as genai
import os
import json
from functools import lru_cache
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
ENABLE_LLM = os.getenv('ENABLE_LLM', 'true').lower() == 'true'

# Model configuration
# Model selection with fallback
# Primary model can be overridden with LLM_MODEL env. Fallback can be set via LLM_MODEL_FALLBACK
MODEL_NAME = os.getenv('LLM_MODEL', 'gemini-2.5-pro')
MODEL_FALLBACK = os.getenv('LLM_MODEL_FALLBACK', 'gemini-2.0-flash-exp')
GENERATION_CONFIG = {
    'temperature': 0.3,  # More consistent, less creative
    'max_output_tokens': 4096,  # Give enough room to avoid early truncation
    'top_p': 0.8,
}

# Rate limiting tracking
_rate_limit_tracker = {
    'requests': [],
    'max_per_minute': 15  # Gemini free tier: 15 RPM
}

# Cached model instances per model name
_model_instances = {}


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
        logger.info(f"Gemini API initialized successfully. Primary model: {MODEL_NAME}; Fallback: {MODEL_FALLBACK}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {str(e)}")
        return False


def get_model(model_name: str = None):
    """
    Get the configured Gemini model instance.
    
    Returns:
        GenerativeModel: Configured model instance or None if not available
    """
    if not initialize_gemini():
        return None
    
    try:
        name = model_name or MODEL_NAME
        if name not in _model_instances:
            _model_instances[name] = genai.GenerativeModel(name)
        return _model_instances[name]
    except Exception as e:
        logger.error(f"Failed to create model instance '{model_name or MODEL_NAME}': {str(e)}")
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
    fallback = _contextual_fallback_question(placeholder_name, '')
    
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
        # Create prompt
        prompt = f"""Convert this placeholder name into a clear, professional question for a legal document.

The question should:
- Be concise (one sentence)
- Be professional and formal in tone
- Clearly indicate what information is needed
- Be suitable for a legal document context

Placeholder name: {placeholder_name}

Generate only the question, nothing else:"""
        
        # Generate content with timeout (with model fallback)
        try:
            response, used_model = _generate_with_fallback(prompt, GENERATION_CONFIG, 3)
            
            # Extract text
            question = _extract_response_text(response)
            if question:
                question = question.strip()
                
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
        
        # Generate content with timeout (with model fallback)
        try:
            response, used_model = _generate_with_fallback(prompt, GENERATION_CONFIG, 5)
            
            # Parse response
            response_text = _extract_response_text(response)
            if response_text:
                response_text = response_text.strip()
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


# ===== New Hybrid Validation and Context-Aware Question APIs =====

def _clip_text(text: str, max_len: int = 400) -> str:
    t = (text or '').strip()
    return t[:max_len]


def _extract_response_text(resp) -> str:
    """
    Robustly extract text from a Gemini response.
    Avoids using resp.text quick accessor which raises when no valid Part exists.
    Returns an empty string if no text is available.
    """
    try:
        if not resp:
            return ''
        # Preferred: use candidates → content → parts → text
        candidates = getattr(resp, 'candidates', None)
        if candidates and len(candidates) > 0:
            for cand in candidates:
                content = getattr(cand, 'content', None)
                if not content:
                    continue
                parts = getattr(content, 'parts', None)
                if parts and len(parts) > 0:
                    # Find first text part
                    for p in parts:
                        txt = getattr(p, 'text', None)
                        if isinstance(txt, str) and txt.strip():
                            return txt.strip()
        # Fallback: try quick accessor if available
        txt = getattr(resp, 'text', None)
        if isinstance(txt, str):
            return txt.strip()
    except Exception:
        # Swallow and fallback to empty
        pass
    return ''


def _model_sequence() -> list:
    """Return the list of models to try in order."""
    seq = [MODEL_NAME]
    if MODEL_FALLBACK and MODEL_FALLBACK not in seq:
        seq.append(MODEL_FALLBACK)
    return seq


def _generate_with_fallback(prompt: str, gen_config: dict, timeout_seconds: int) -> tuple:
    """
    Try generating content using primary model, then fallback models on error/timeout.
    Returns (response, model_name) or (None, None) if all failed.
    """
    models = _model_sequence()
    logger.info("Attempting generation with model sequence: %s (timeout: %ds)", models, timeout_seconds)
    for name in models:
        try:
            logger.info("Trying model: %s", name)
            model = get_model(name)
            if not model:
                logger.warning(f"Model '{name}' not available; trying next")
                continue
            record_request()
            logger.info("Sending request to model '%s'...", name)
            resp = model.generate_content(
                prompt,
                generation_config=gen_config,
                request_options={'timeout': timeout_seconds}
            )
            logger.info("Model '%s' responded successfully", name)
            logger.info("Raw response from API: %s", resp)
            return resp, name
        except Exception as e:
            logger.warning(f"Generation failed on model '{name}': {e}", exc_info=True)
            continue
    logger.error("All models in sequence failed to generate content")
    return None, None


def _fallback_question(normalized: str) -> str:
    """Simple fallback question when LLM is unavailable."""
    key = (normalized or '').strip()
    if not key:
        return "What information should be provided?"
    friendly = key.replace('_', ' ').replace('-', ' ').strip()
    if not friendly:
        return "What information should be provided?"
    title = friendly[0].upper() + friendly[1:]
    return f"Please provide: {title}"


def _prepare_batch_payload(items: list) -> str:
    """Serialize batch request payload as JSON string for the LLM prompt.
    
    Deduplicates sentence context to reduce payload size. Sentences are
    indexed and referenced by ID in the items array.
    """
    # Group placeholders by their sentence context (using a hash of prev+sentence+next)
    sentence_map = {}  # hash -> {id, prev, sentence, next}
    sentence_id_counter = 1
    
    structured_items = []
    for item in items:
        context = item.get('context') or {}
        prev = _clip_text(context.get('prev', ''), 220)
        sentence = _clip_text(context.get('sentence', ''), 320)
        next_ = _clip_text(context.get('next', ''), 220)
        
        # Create a stable hash of the context
        context_hash = hash((prev, sentence, next_))
        
        # Register sentence if not seen before
        if context_hash not in sentence_map:
            sentence_map[context_hash] = {
                "id": sentence_id_counter,
                "previous": prev,
                "sentence": sentence,
                "next": next_
            }
            sentence_id_counter += 1
        
        # Reference the sentence by ID
        structured_items.append({
            "placeholder": item.get('normalized', ''),
            "pattern": item.get('pattern_type', ''),
            "original": item.get('original', ''),
            "sentence_id": sentence_map[context_hash]["id"]
        })
    
    # Build final payload
    sentences_array = sorted(sentence_map.values(), key=lambda x: x["id"])
    payload = {
        "sentences": sentences_array,
        "items": structured_items
    }
    
    return json.dumps(payload, ensure_ascii=False)


def generate_questions_for_candidates(items: list, use_llm: bool = True) -> dict:
    """Generate questions for a list of detected placeholder candidates.

    Args:
        items: List of dicts with keys: normalized, original, pattern_type, context(prev/sentence/next).
        use_llm: Whether to attempt LLM generation.

    Returns:
        dict[str, dict]: {normalized: {'question': str, 'source': 'llm'|'fallback', 'model': str|None}}
    """
    results = {}
    if not items:
        return results

    # Deduplicate by normalized key while preserving order
    deduped = []
    seen = set()
    for item in items:
        key = item.get('normalized') or ''
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    # Seed results with fallbacks
    for item in deduped:
        key = item.get('normalized') or ''
        results[key] = {
            'question': _fallback_question(key),
            'source': 'fallback',
            'model': None
        }

    if not use_llm or not is_llm_enabled():
        return results

    allowed, wait_seconds = check_rate_limit()
    if not allowed:
        logger.warning("Rate limit hit before batch question generation; using fallbacks")
        return results

    payload_json = _prepare_batch_payload(deduped)
    logger.info("=== BATCH QUESTION GENERATION START ===")
    logger.info("Preparing to generate questions for %d placeholders", len(deduped))
    logger.info("Batch question payload:\n%s", payload_json)
    prompt = (
        "You generate concise, professional questions that a legal assistant will ask a user to fill in placeholders in a document.\n"
        "Below is a JSON object with two arrays:\n"
        "- `sentences`: Contains unique sentence contexts, each with an `id`, `previous`, `sentence`, and `next` text.\n"
        "- `items`: Contains placeholders, each referencing a sentence by `sentence_id`.\n\n"
        "For each item in `items`, write ONE clear, professional question that gathers the information needed to fill that placeholder.\n"
        "Guidelines:\n"
        "- Use the placeholder name, pattern, original text, and the referenced sentence context to understand what is needed.\n"
        "- Each question must be a single sentence, end with appropriate punctuation, and NOT include example answers.\n"
        "- If sentence context is empty, infer from the placeholder name.\n"
        "Return ONLY a JSON object where each key is the placeholder name and each value is the question string.\n\n"
        f"data: {payload_json}\n"
    )

    try:
        logger.info("Calling LLM with prompt (truncated first 500 chars):\n%s...", prompt[:500])
        resp, model_used = _generate_with_fallback(prompt, GENERATION_CONFIG, 20)
        logger.info("LLM responded, model used: %s", model_used)
        response_text = _extract_response_text(resp)
        logger.info("Extracted response text (length: %d chars):\n%s", len(response_text), response_text[:1000] if response_text else "(empty)")
        if not response_text:
            logger.warning("Batch question generation returned empty response; retaining fallbacks")
            return results

        # Clean markdown code fences (```json ... ```) that some models add
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```'):
            # Remove opening fence (```json or ```)
            lines = cleaned_text.split('\n', 1)
            if len(lines) > 1:
                cleaned_text = lines[1]
            else:
                cleaned_text = cleaned_text[3:]  # Just remove ```
        if cleaned_text.endswith('```'):
            # Remove closing fence
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        if cleaned_text != response_text:
            logger.info("Cleaned markdown fences from response")

        try:
            data = json.loads(cleaned_text)
            logger.info("Successfully parsed JSON response, keys found: %s", list(data.keys()))
        except json.JSONDecodeError as e:
            logger.warning("Batch question generation returned non-JSON response; retaining fallbacks. Error: %s", e)
            logger.warning("Attempted to parse: %s", cleaned_text[:500])
            return results

        for item in deduped:
            key = item.get('normalized') or ''
            proposed = data.get(key)
            if isinstance(proposed, dict):
                question_text = proposed.get('question') or proposed.get('q')
            else:
                question_text = proposed

            if isinstance(question_text, str):
                clean = question_text.strip().strip('\"\'')
                if clean:
                    if clean[-1] not in {'.', '?', '!'}:
                        clean += '?'
                    if len(clean) <= 600:
                        results[key] = {
                            'question': clean,
                            'source': 'llm',
                            'model': model_used
                        }
        llm_count = sum(1 for v in results.values() if v['source'] == 'llm')
        fallback_count = sum(1 for v in results.values() if v['source'] == 'fallback')
        logger.info("=== BATCH QUESTION GENERATION COMPLETE ===")
        logger.info("Total placeholders: %d, LLM-generated: %d, Fallback: %d, Model: %s", 
                   len(deduped), llm_count, fallback_count, model_used if llm_count else 'N/A')
        if llm_count > 0:
            logger.info("Sample LLM questions:")
            for i, (k, v) in enumerate(results.items()):
                if v['source'] == 'llm' and i < 3:  # Show first 3 LLM questions
                    logger.info("  - %s: %s", k, v['question'])
        return results
    except Exception as exc:
        logger.error(f"Batch question generation failed with exception: {exc}", exc_info=True)
        return results


def _contextual_fallback_question(normalized: str, sentence: str = '') -> str:
    """Generate a conversational fallback question using placeholder name + context."""
    normalized = normalized or ''
    clean_name = normalized.replace('_', ' ').replace('-', ' ').strip()
    sentence = (sentence or '').strip()

    # Provide useful snippet when available
    snippet = ''
    if sentence:
        snippet = sentence[:120]
        if len(sentence) > 120:
            snippet += '...'

    # Handle generic blanks
    if normalized.startswith(('blank_', 'field_', 'amount_')) or clean_name.lower() in {'blank', 'field'}:
        if snippet:
            return f"What information should fill this blank? Context: \"{snippet}\""
        return "What information should fill this blank?"

    keywords = {
        'name': "What is the full name?",
        'company': "What is the company name?",
        'date': "What is the relevant date? (e.g., January 1, 2024)",
        'address': "What is the complete address?",
        'email': "What is the email address?",
        'phone': "What is the phone number?",
        'amount': "What is the amount? (e.g., $1,000.00)",
        'title': "What is the title or position?",
        'signature': "Who should sign here?",
        'party': "What is the party's name?",
        'effective': "What is the effective date?",
        'term': "What is the term or duration?",
        'address': "What is the full address?"
    }

    lowered = clean_name.lower()
    for key, question in keywords.items():
        if key in lowered and key != 'blank':
            if snippet:
                return f"{question} Context: \"{snippet}\""
            return question

    if clean_name:
        question = f"What is the {clean_name}?"
        if snippet:
            question += f" Context: \"{snippet}\""
        return question

    # Last resort
    if snippet:
        return f"What information should be provided here? Context: \"{snippet}\""
    return "What information should be provided here?"


@lru_cache(maxsize=512)
def generate_question_from_context(normalized: str, sentence: str, prev: str = '', next_: str = '', options: tuple = None, use_llm: bool = True) -> dict:
    """
    Generate a context-aware question.
    Returns dict: { 'question': str, 'options': list[str] | None }
    - If options provided, craft a single-select question.
    Fallback: simple question formatting.
    """
    normalized = normalized or ''
    fallback_q = _contextual_fallback_question(normalized, sentence)
    if options:
        try:
            opts = list(options)
        except Exception:
            opts = []
        if opts:
            fallback_q = f"Please select one of the following options: {', '.join(opts)}"

    if not use_llm or not is_llm_enabled():
        return {'question': fallback_q, 'options': list(options) if options else None}

    allowed, wait_seconds = check_rate_limit()
    if not allowed:
        return {'question': fallback_q, 'options': list(options) if options else None}

    # We'll try with fallback sequence

    context_prev = _clip_text(prev, 300)
    context_sentence = _clip_text(sentence, 400)
    context_next = _clip_text(next_, 300)
    options_part = ''
    if options:
        options_list = ', '.join(list(options))
        options_part = f"\nOptions (single-select): {options_list}\n"

    prompt = f"""
Craft a concise, professional question (one sentence) to collect user input for a legal document field.
Use only the provided minimal context. Do not include suggestions or sample answers.
If options are provided, ask as a single-select and list the options explicitly.

Field key: {normalized}
Context:
Previous: {context_prev}
Sentence: {context_sentence}
Next: {context_next}
{options_part}
Return only the question text.
"""

    try:
        # PII-safe debug logging: only lengths, not content
        try:
            logger.debug(
                "generate_question_from_context: lens prev=%d sent=%d next=%d opts=%d",
                len(context_prev), len(context_sentence), len(context_next), len(options) if options else 0
            )
        except Exception:
            pass
        resp, used_model = _generate_with_fallback(prompt, GENERATION_CONFIG, 4)
        q = _extract_response_text(resp).strip().strip('\n').strip('"\'"')
        if q and not q.endswith(('?', '.', '!')):
            q += '?'
        if not q:
            q = fallback_q
        return {'question': q, 'options': list(options) if options else None}
    except Exception as e:
        logger.warning(f"generate_question_from_context LLM error: {e}")
        return {'question': fallback_q, 'options': list(options) if options else None}

