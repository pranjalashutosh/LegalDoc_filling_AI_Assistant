"""
Conversation API Routes
Handles conversational placeholder filling endpoints
"""

from flask import Blueprint, request, session, jsonify
from lib.llm_service import generate_question, is_llm_enabled
from lib.error_handlers import handle_api_error, SessionExpiredError
import logging

logger = logging.getLogger(__name__)

# Create blueprint
conversation_bp = Blueprint('conversation', __name__)


@conversation_bp.route('/api/conversation/next', methods=['GET'])
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
        
        # Determine if LLM should be used
        should_use_llm = use_llm_param and is_llm_enabled()
        
        # Generate question
        if should_use_llm:
            try:
                question = generate_question(placeholder, use_llm=True)
                logger.info(f"Generated LLM question for placeholder: {placeholder}")
            except Exception as llm_error:
                logger.warning(f"LLM generation failed, using fallback: {llm_error}")
                question = f"Please provide: {placeholder}"
        else:
            # Simple fallback question
            question = f"Please provide: {placeholder}"
            logger.info(f"Generated simple question for placeholder: {placeholder}")
        
        return jsonify({
            'success': True,
            'placeholder': placeholder,
            'question': question,
            'used_llm': should_use_llm
        }), 200
        
    except SessionExpiredError as e:
        return handle_api_error(e, 'Session expired')
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        return handle_api_error(e, 'Failed to generate question')


@conversation_bp.route('/api/conversation/answer', methods=['POST'])
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


@conversation_bp.route('/api/conversation/status', methods=['GET'])
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


@conversation_bp.route('/api/conversation/answers', methods=['GET'])
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


@conversation_bp.route('/api/conversation/reset', methods=['POST'])
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

