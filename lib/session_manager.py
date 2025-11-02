"""
Session Manager
Handles session lifecycle, storage, and cleanup for the application
"""

from flask import session
import os
import time
import logging
from datetime import datetime, timedelta
from config import Config
import uuid

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions for the document filler application.
    Handles session initialization, data storage, timeout checking, and cleanup.
    """
    
    def __init__(self, app=None):
        """
        Initialize the session manager.
        
        Args:
            app: Flask application instance (optional)
        """
        self.app = app
        self.session_timeout = Config.SESSION_TIMEOUT
        self.upload_folder = Config.UPLOAD_FOLDER
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize the session manager with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Register cleanup handler
        @app.before_request
        def check_session_timeout():
            """Check if session has timed out before each request."""
            if self.is_session_expired():
                self.clear_session()
    
    def initialize_session(self):
        """
        Initialize a new session with a unique ID and timestamp.
        
        Returns:
            str: The session ID
        """
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        session['created_at'] = datetime.now().isoformat()
        session['last_activity'] = datetime.now().isoformat()
        session.modified = True
        
        logger.info(f"Initialized new session: {session_id}")
        return session_id
    
    def get_session_id(self):
        """
        Get the current session ID, creating one if it doesn't exist.
        
        Returns:
            str: The session ID
        """
        if 'session_id' not in session:
            return self.initialize_session()
        return session.get('session_id')
    
    def update_activity(self):
        """
        Update the last activity timestamp for the current session.
        """
        session['last_activity'] = datetime.now().isoformat()
        session.modified = True
    
    def is_session_expired(self):
        """
        Check if the current session has expired due to inactivity.
        
        Returns:
            bool: True if session is expired, False otherwise
        """
        if 'last_activity' not in session:
            return False
        
        try:
            last_activity = datetime.fromisoformat(session['last_activity'])
            timeout = timedelta(seconds=self.session_timeout)
            
            is_expired = datetime.now() - last_activity > timeout
            
            if is_expired:
                logger.info(f"Session expired: {session.get('session_id')}")
            
            return is_expired
        except (ValueError, TypeError) as e:
            logger.error(f"Error checking session expiration: {e}")
            return False
    
    def store_file_path(self, filename):
        """
        Store the uploaded file path in the session.
        
        Args:
            filename (str): The filename to store
        """
        session['filename'] = filename
        session.modified = True
        self.update_activity()
        logger.debug(f"Stored filename in session: {filename}")
    
    def store_placeholders(self, placeholders):
        """
        Store detected placeholders in the session.
        
        Args:
            placeholders (list): List of placeholder names
        """
        session['placeholders'] = placeholders
        session.modified = True
        self.update_activity()
        logger.debug(f"Stored {len(placeholders)} placeholders in session")
    
    def store_answer(self, placeholder, answer):
        """
        Store a single placeholder answer in the session.
        
        Args:
            placeholder (str): The placeholder name
            answer (str): The user's answer
        """
        if 'answers' not in session:
            session['answers'] = {}
        
        session['answers'][placeholder] = answer
        session.modified = True
        self.update_activity()
        logger.debug(f"Stored answer for placeholder: {placeholder}")
    
    def store_answers(self, answers):
        """
        Store multiple placeholder answers in the session.
        
        Args:
            answers (dict): Dictionary of placeholder -> answer mappings
        """
        session['answers'] = answers
        session.modified = True
        self.update_activity()
        logger.debug(f"Stored {len(answers)} answers in session")
    
    def get_filename(self):
        """
        Get the stored filename from the session.
        
        Returns:
            str: The filename, or None if not found
        """
        return session.get('filename')
    
    def get_placeholders(self):
        """
        Get the stored placeholders from the session.
        
        Returns:
            list: List of placeholder names, or empty list if not found
        """
        return session.get('placeholders', [])
    
    def get_answers(self):
        """
        Get the stored answers from the session.
        
        Returns:
            dict: Dictionary of placeholder -> answer mappings, or empty dict if not found
        """
        return session.get('answers', {})
    
    def get_answer(self, placeholder):
        """
        Get the answer for a specific placeholder.
        
        Args:
            placeholder (str): The placeholder name
        
        Returns:
            str: The answer, or None if not found
        """
        answers = self.get_answers()
        return answers.get(placeholder)
    
    def has_uploaded_file(self):
        """
        Check if a file has been uploaded in this session.
        
        Returns:
            bool: True if a file is uploaded, False otherwise
        """
        filename = self.get_filename()
        if not filename:
            return False
        
        file_path = os.path.join(self.upload_folder, filename)
        return os.path.exists(file_path)
    
    def has_placeholders(self):
        """
        Check if placeholders have been detected in this session.
        
        Returns:
            bool: True if placeholders exist, False otherwise
        """
        placeholders = self.get_placeholders()
        return len(placeholders) > 0
    
    def has_all_answers(self):
        """
        Check if all placeholders have been answered.
        
        Returns:
            bool: True if all placeholders are answered, False otherwise
        """
        placeholders = self.get_placeholders()
        answers = self.get_answers()
        
        if not placeholders:
            return False
        
        for placeholder in placeholders:
            if placeholder not in answers or not answers[placeholder]:
                return False
        
        return True
    
    def get_progress(self):
        """
        Get the current progress through the conversation.
        
        Returns:
            dict: Dictionary with 'total', 'filled', 'remaining', 'percentage'
        """
        placeholders = self.get_placeholders()
        answers = self.get_answers()
        
        total = len(placeholders)
        filled = len([p for p in placeholders if p in answers and answers[p]])
        remaining = total - filled
        percentage = (filled / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'filled': filled,
            'remaining': remaining,
            'percentage': round(percentage, 1)
        }
    
    def clear_session(self):
        """
        Clear all session data and clean up associated files.
        """
        session_id = session.get('session_id')
        
        # Clean up uploaded file
        filename = self.get_filename()
        if filename:
            file_path = os.path.join(self.upload_folder, filename)
            self._cleanup_file(file_path)
        
        # Clean up completed document if exists
        completed_path = session.get('completed_path')
        if completed_path:
            self._cleanup_file(completed_path)
        
        # Clear session data
        session.clear()
        
        logger.info(f"Cleared session: {session_id}")
    
    def _cleanup_file(self, file_path):
        """
        Clean up a single file.
        
        Args:
            file_path (str): Path to the file to remove
        """
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to clean up file {file_path}: {e}")
    
    def cleanup_expired_files(self, max_age_hours=24):
        """
        Clean up files older than the specified age.
        This should be run periodically as a background task.
        
        Args:
            max_age_hours (int): Maximum file age in hours before cleanup
        """
        try:
            now = time.time()
            max_age_seconds = max_age_hours * 3600
            cleanup_count = 0
            
            if not os.path.exists(self.upload_folder):
                return
            
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                
                if not os.path.isfile(file_path):
                    continue
                
                file_age = now - os.path.getmtime(file_path)
                
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        cleanup_count += 1
                        logger.info(f"Cleaned up expired file: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to clean up expired file {filename}: {e}")
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} expired files")
        
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
    
    def get_session_info(self):
        """
        Get information about the current session.
        
        Returns:
            dict: Dictionary with session information
        """
        return {
            'session_id': session.get('session_id'),
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity'),
            'has_file': self.has_uploaded_file(),
            'has_placeholders': self.has_placeholders(),
            'has_all_answers': self.has_all_answers(),
            'progress': self.get_progress()
        }


# Global session manager instance
session_manager = SessionManager()

