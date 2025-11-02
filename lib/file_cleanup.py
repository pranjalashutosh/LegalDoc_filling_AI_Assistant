"""
File Cleanup Utilities
Handles cleanup of temporary files, uploaded documents, and orphaned files
"""

import os
import time
import logging
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)


class FileCleanup:
    """
    Manages cleanup of temporary and expired files.
    """
    
    def __init__(self, upload_folder=None):
        """
        Initialize the file cleanup manager.
        
        Args:
            upload_folder (str): Path to the upload folder (default: from Config)
        """
        self.upload_folder = upload_folder or Config.UPLOAD_FOLDER
    
    def cleanup_expired_files(self, max_age_hours=24):
        """
        Clean up files older than the specified age.
        
        Args:
            max_age_hours (int): Maximum file age in hours before cleanup
        
        Returns:
            dict: Summary of cleanup operation
        """
        try:
            if not os.path.exists(self.upload_folder):
                logger.warning(f"Upload folder does not exist: {self.upload_folder}")
                return {
                    'success': False,
                    'files_cleaned': 0,
                    'error': 'Upload folder not found'
                }
            
            now = time.time()
            max_age_seconds = max_age_hours * 3600
            
            files_cleaned = 0
            errors = []
            
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                
                # Skip directories
                if not os.path.isfile(file_path):
                    continue
                
                try:
                    # Get file modification time
                    file_age = now - os.path.getmtime(file_path)
                    
                    # Check if file is expired
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        files_cleaned += 1
                        logger.info(f"Cleaned up expired file: {filename} (age: {file_age/3600:.1f} hours)")
                
                except Exception as e:
                    error_msg = f"Failed to clean up {filename}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(f"File cleanup complete: {files_cleaned} files removed")
            
            return {
                'success': True,
                'files_cleaned': files_cleaned,
                'errors': errors if errors else None
            }
        
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
            return {
                'success': False,
                'files_cleaned': 0,
                'error': str(e)
            }
    
    def cleanup_specific_file(self, filename):
        """
        Clean up a specific file by name.
        
        Args:
            filename (str): Name of the file to clean up
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.upload_folder, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up specific file: {filename}")
                return True
            else:
                logger.warning(f"File not found for cleanup: {filename}")
                return False
        
        except Exception as e:
            logger.error(f"Error cleaning up {filename}: {e}")
            return False
    
    def cleanup_file_by_path(self, file_path):
        """
        Clean up a file by its full path.
        
        Args:
            file_path (str): Full path to the file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
                return True
            else:
                logger.warning(f"File not found for cleanup: {file_path}")
                return False
        
        except Exception as e:
            logger.error(f"Error cleaning up {file_path}: {e}")
            return False
    
    def cleanup_session_files(self, session_data):
        """
        Clean up all files associated with a session.
        
        Args:
            session_data (dict): Session data containing file references
        
        Returns:
            dict: Summary of cleanup operation
        """
        try:
            files_cleaned = 0
            errors = []
            
            # Clean up uploaded file
            if 'filename' in session_data:
                filename = session_data['filename']
                if self.cleanup_specific_file(filename):
                    files_cleaned += 1
                else:
                    errors.append(f"Failed to clean up uploaded file: {filename}")
            
            # Clean up completed document
            if 'completed_path' in session_data:
                completed_path = session_data['completed_path']
                if self.cleanup_file_by_path(completed_path):
                    files_cleaned += 1
                else:
                    errors.append(f"Failed to clean up completed document: {completed_path}")
            
            return {
                'success': True,
                'files_cleaned': files_cleaned,
                'errors': errors if errors else None
            }
        
        except Exception as e:
            logger.error(f"Error cleaning up session files: {e}")
            return {
                'success': False,
                'files_cleaned': 0,
                'error': str(e)
            }
    
    def get_folder_stats(self):
        """
        Get statistics about the upload folder.
        
        Returns:
            dict: Folder statistics
        """
        try:
            if not os.path.exists(self.upload_folder):
                return {
                    'exists': False,
                    'total_files': 0,
                    'total_size_bytes': 0
                }
            
            total_files = 0
            total_size = 0
            oldest_file = None
            oldest_age = 0
            
            now = time.time()
            
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                
                if os.path.isfile(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
                    
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > oldest_age:
                        oldest_age = file_age
                        oldest_file = filename
            
            return {
                'exists': True,
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_file': oldest_file,
                'oldest_file_age_hours': round(oldest_age / 3600, 2) if oldest_file else 0
            }
        
        except Exception as e:
            logger.error(f"Error getting folder stats: {e}")
            return {
                'error': str(e)
            }
    
    def cleanup_after_download(self, session_data):
        """
        Clean up completed document after successful download.
        Keeps the original uploaded file.
        
        Args:
            session_data (dict): Session data containing file references
        
        Returns:
            bool: True if successful
        """
        try:
            completed_path = session_data.get('completed_path')
            
            if completed_path:
                return self.cleanup_file_by_path(completed_path)
            
            return True  # Nothing to clean up
        
        except Exception as e:
            logger.error(f"Error cleaning up after download: {e}")
            return False


# Global file cleanup instance
file_cleanup = FileCleanup()


def schedule_periodic_cleanup(app, interval_hours=24, max_age_hours=24):
    """
    Schedule periodic file cleanup (for production use with task scheduler).
    
    Note: This is a simple implementation. In production, consider using:
    - APScheduler for in-process scheduling
    - Celery for distributed task queue
    - Cron jobs for server-side scheduling
    
    Args:
        app: Flask application instance
        interval_hours (int): How often to run cleanup (hours)
        max_age_hours (int): Maximum file age before cleanup (hours)
    """
    import threading
    import time as time_module
    
    def cleanup_task():
        """Background cleanup task."""
        while True:
            try:
                with app.app_context():
                    logger.info("Running scheduled file cleanup...")
                    result = file_cleanup.cleanup_expired_files(max_age_hours)
                    logger.info(f"Scheduled cleanup complete: {result}")
            except Exception as e:
                logger.error(f"Error in scheduled cleanup: {e}")
            
            # Sleep until next interval
            time_module.sleep(interval_hours * 3600)
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    logger.info(f"Scheduled periodic cleanup: every {interval_hours} hours, max age {max_age_hours} hours")

