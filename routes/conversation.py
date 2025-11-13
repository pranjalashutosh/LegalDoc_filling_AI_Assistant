"""
Conversation API Routes
Handles conversational placeholder filling endpoints
"""

from flask import Blueprint, request, session, jsonify
from lib.llm_service import (
    is_llm_enabled,
    generate_questions_for_candidates,
)
from lib.error_handlers import handle_api_error, SessionExpiredError
import logging

logger = logging.getLogger(__name__)

# Create blueprint
conversation_bp = Blueprint('conversation', __name__)


def _generate_smart_fallback(placeholder: str, sentence: str = '') -> str:
    """
    Generate a more conversational fallback question when LLM is unavailable.
    Uses the placeholder name and surrounding context to create a natural question.
    """
    # Clean up placeholder name
    clean_name = placeholder.replace('_', ' ').replace('-', ' ').strip()
    
    # Check if it's a generic "blank" or "field" placeholder
    if placeholder.startswith(('blank_', 'field_', 'amount_')):
        # Try to extract context from sentence
        if sentence and len(sentence) > 10:
            # Show a snippet of the sentence for context
            snippet = sentence[:100] + ('...' if len(sentence) > 100 else '')
            return f"What should be filled in here?\n\nContext: \"{snippet}\""
        else:
            return f"What information should go in this field?"
    
    # For named placeholders, create a conversational question
    words = clean_name.split()
    
    # Common field types with better questions
    field_questions = {
        'name': "What is the full name?",
        'company': "What is the company name?",
        'date': "What is the date? (e.g., January 1, 2024)",
        'address': "What is the complete address?",
        'email': "What is the email address?",
        'phone': "What is the phone number?",
        'amount': "What is the amount? (e.g., $1,000.00)",
        'title': "What is the title or position?",
        'signature': "Who should sign this document?",
        'party': "What is the party's name?",
        'effective': "What is the effective date?",
        'term': "What is the term or duration?",
    }
    
    # Check if any keyword matches
    for keyword, question in field_questions.items():
        if keyword in clean_name.lower():
            # Customize based on full name
            if len(words) > 1:
                return f"What is the {clean_name}?"
            return question
    
    # Default: make it conversational
    if len(words) == 1:
        return f"What is the {clean_name}?"
    else:
        return f"Please provide the {clean_name}:"


@conversation_bp.route('/conversation/next', methods=['GET'])
def get_next_question():
    """
    Get the next question for a placeholder
    Query params:
        - placeholder: The placeholder name
        - use_llm: Whether to use LLM (default: true)
    Returns:
        JSON with question text
    """
    try:
        # Get placeholder name from query params
        placeholder = request.args.get('placeholder', '')
        use_llm_param = request.args.get('use_llm', 'true').lower() == 'true'
        
        if not placeholder:
            return jsonify({
                'success': False,
                'error': 'Placeholder name is required'
            }), 400
        
        # Check if placeholders exist in session
        placeholders = session.get('placeholders', [])
        if not placeholders:
            raise SessionExpiredError('No placeholders found in session. Please upload a document.')
        
        if placeholder not in placeholders:
            return jsonify({
                'success': False,
                'error': f'Placeholder "{placeholder}" not found in session'
            }), 404
        
        # Determine if LLM should be used for this response
        should_use_llm = use_llm_param and is_llm_enabled()

        # Attempt to use context from detection for question crafting
        details = session.get('placeholder_details') or {}
        groups = details.get('groups') or {}
        candidates = details.get('candidates') or []
        questions_cache = details.get('questions') or {}
        question_sources = details.get('question_sources') or {}
        question_models = details.get('question_models') or {}

        # Pick a representative candidate for this canonical key
        selected_context = {'prev': '', 'sentence': '', 'next': ''}
        selected_candidate = None
        try:
            ids_for_key = groups.get(placeholder) or []
            selected_id = ids_for_key[0] if ids_for_key else None

            if selected_id:
                cand = next((c for c in candidates if c.get('id') == selected_id), None)
                if cand and 'context' in cand:
                    selected_context = cand['context']
                    selected_candidate = cand
        except Exception as ctx_err:
            logger.debug(f"Context selection error: {ctx_err}")

        if not selected_candidate:
            selected_candidate = next((c for c in candidates if c.get('normalized') == placeholder), None)
            if selected_candidate and 'context' in selected_candidate and selected_candidate['context']:
                selected_context = selected_candidate['context']

        # Heuristic extraction of simple radio/check options from sentence
        def extract_options(sentence_text: str):
            try:
                import re
                s = (sentence_text or '').strip()
                # pattern like Male/Female or Yes/No
                m = re.findall(r"\b([A-Z][a-zA-Z]+)\s*/\s*([A-Z][a-zA-Z]+)\b", s)
                if m and len(m[0]) == 2:
                    return [m[0][0], m[0][1]]
                # pattern like options in parentheses: (Option A, Option B)
                m2 = re.search(r"\(([A-Za-z][A-Za-z0-9 ,/]+)\)", s)
                if m2:
                    parts = [p.strip() for p in re.split(r",|/| or ", m2.group(1))]
                    parts = [p for p in parts if len(p) > 0 and len(p) <= 30]
                    if 1 < len(parts) <= 6:
                        return parts
            except Exception:
                pass
            return None

        options = extract_options(selected_context.get('sentence'))

        cached_question = questions_cache.get(placeholder)
        source = question_sources.get(placeholder, 'fallback')
        llm_model = question_models.get(placeholder)

        question = None
        used_llm = False

        if not should_use_llm:
            question = _generate_smart_fallback(placeholder, selected_context.get('sentence', ''))
        else:
            if cached_question:
                question = cached_question
                used_llm = source == 'llm'
            if (not question) or (source != 'llm'):
                try:
                    regen_item = [{
                        'normalized': placeholder,
                        'original': (selected_candidate or {}).get('original', ''),
                        'pattern_type': (selected_candidate or {}).get('pattern_type', ''),
                        'context': selected_context
                    }]
                    regen_result = generate_questions_for_candidates(regen_item)
                    regen_entry = regen_result.get(placeholder)
                    if regen_entry and regen_entry.get('question'):
                        question = regen_entry['question']
                        source = regen_entry.get('source', 'fallback')
                        llm_model = regen_entry.get('model')
                        used_llm = source == 'llm'
                        questions_cache[placeholder] = question
                        question_sources[placeholder] = source
                        if llm_model:
                            question_models[placeholder] = llm_model
                        elif placeholder in question_models:
                            question_models.pop(placeholder, None)
                        session['placeholder_details']['questions'] = questions_cache
                        session['placeholder_details']['question_sources'] = question_sources
                        session['placeholder_details']['question_models'] = question_models
                        session.modified = True
                except Exception as llm_error:
                    logger.warning(f"Regeneration for {placeholder} failed: {llm_error}")
            if not question:
                question = _generate_smart_fallback(placeholder, selected_context.get('sentence', ''))
                used_llm = False
                llm_model = None

        if not should_use_llm:
            used_llm = False
            llm_model = None
        
        return jsonify({
            'success': True,
            'placeholder': placeholder,
            'question': question,
            'used_llm': used_llm,
            'llm_model': llm_model if used_llm else None,
            'options': options if options else None
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        return handle_api_error(e, 'Failed to generate question')


@conversation_bp.route('/conversation/answer', methods=['POST'])
def submit_answer():
    """
    Submit an answer for a placeholder
    Body:
        - placeholder: The placeholder name
        - answer: The user's answer
    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        placeholder = data.get('placeholder', '').strip()
        answer = data.get('answer', '').strip()
        
        # Validate input
        if not placeholder:
            return jsonify({
                'success': False,
                'error': 'Placeholder name is required'
            }), 400
        
        if not answer:
            return jsonify({
                'success': False,
                'error': 'Answer is required'
            }), 400
        
        # Check if placeholders exist in session
        placeholders = session.get('placeholders', [])
        if not placeholders:
            raise SessionExpiredError('No placeholders found in session')
        
        if placeholder not in placeholders:
            return jsonify({
                'success': False,
                'error': f'Placeholder "{placeholder}" not found in session'
            }), 404
        
        # Store answer in session
        if 'answers' not in session:
            session['answers'] = {}
        
        session['answers'][placeholder] = answer
        session.modified = True
        
        logger.info(f"Stored answer for placeholder: {placeholder}")
        
        return jsonify({
            'success': True,
            'placeholder': placeholder,
            'message': 'Answer stored successfully'
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return handle_api_error(e, 'Failed to submit answer')


@conversation_bp.route('/conversation/answer/instance', methods=['POST'])
def submit_instance_override():
    """
    Submit an answer override for a specific placeholder instance (single occurrence).
    Body:
        - instance_id: Stable ID from detection (e.g., t0-r1-c2-p3-s10-e20)
        - normalized: Canonical placeholder key this instance belongs to
        - answer: The user's answer for this specific instance
    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        instance_id = (data.get('instance_id') or '').strip()
        normalized = (data.get('normalized') or '').strip()
        answer = (data.get('answer') or '').strip()

        if not instance_id or not normalized or not answer:
            return jsonify({'success': False, 'error': 'instance_id, normalized, and answer are required'}), 400

        # Ensure detection data present
        details = session.get('placeholder_details')
        if not details:
            raise SessionExpiredError('No detection data in session')

        groups = details.get('groups') or {}
        # Validate instance belongs to the normalized group
        valid_group = groups.get(normalized)
        if not valid_group or instance_id not in valid_group:
            return jsonify({'success': False, 'error': 'Invalid instance_id for the provided normalized key'}), 400

        # Store override
        overrides = session.get('answers_overrides') or {}
        overrides[instance_id] = {
            'normalized': normalized,
            'answer': answer
        }
        session['answers_overrides'] = overrides
        session.modified = True

        logger.info(f"Stored per-instance override: {instance_id} -> {normalized}")

        return jsonify({'success': True, 'instance_id': instance_id, 'normalized': normalized}), 200

    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error submitting instance override: {e}")
        return handle_api_error(e, 'Failed to submit instance override')


@conversation_bp.route('/conversation/status', methods=['GET'])
def get_conversation_status():
    """
    Get the current conversation status
    Returns:
        JSON with progress information
    """
    try:
        placeholders = session.get('placeholders', [])
        answers = session.get('answers', {})
        
        if not placeholders:
            raise SessionExpiredError('No placeholders found in session')
        
        total = len(placeholders)
        filled = len([p for p in placeholders if p in answers and answers[p]])
        remaining = total - filled
        progress_percentage = (filled / total * 100) if total > 0 else 0
        
        return jsonify({
            'success': True,
            'total': total,
            'filled': filled,
            'remaining': remaining,
            'progress_percentage': round(progress_percentage, 1),
            'is_complete': filled == total
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error getting conversation status: {e}")
        return handle_api_error(e, 'Failed to get conversation status')


@conversation_bp.route('/conversation/answers', methods=['GET'])
def get_all_answers():
    """
    Get all answers submitted so far
    Returns:
        JSON with all placeholder-answer pairs
    """
    try:
        answers = session.get('answers', {})
        placeholders = session.get('placeholders', [])
        
        if not placeholders:
            raise SessionExpiredError('No placeholders found in session')
        
        return jsonify({
            'success': True,
            'answers': answers,
            'total_placeholders': len(placeholders),
            'answered_count': len(answers)
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error getting answers: {e}")
        return handle_api_error(e, 'Failed to get answers')


@conversation_bp.route('/conversation/reset', methods=['POST'])
def reset_conversation():
    """
    Reset the conversation (clear all answers)
    Returns:
        JSON with success status
    """
    try:
        # Keep placeholders but clear answers
        if 'answers' in session:
            session.pop('answers')
            session.modified = True
        
        logger.info("Conversation reset - all answers cleared")
        
        return jsonify({
            'success': True,
            'message': 'Conversation reset successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        return handle_api_error(e, 'Failed to reset conversation')


@conversation_bp.route('/conversation/llm-status', methods=['GET'])
def get_llm_status():
    """
    Get LLM configuration status for debugging.
    Returns:
        JSON with LLM availability and configuration
    """
    try:
        llm_available = is_llm_enabled()
        import os
        has_api_key = bool(os.getenv('GOOGLE_API_KEY'))
        enable_llm_setting = os.getenv('ENABLE_LLM', 'true')
        
        return jsonify({
            'success': True,
            'llm_enabled': llm_available,
            'has_api_key': has_api_key,
            'enable_llm_env': enable_llm_setting,
            'message': 'LLM is ready' if llm_available else 'LLM is not configured (missing API key or disabled)'
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

