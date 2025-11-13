"""
Legal Document Filler - Main Flask Application
Main entry point for the web application.
"""

from flask import Flask, session, jsonify
from config import get_config
import logging
import os
import secrets

# Configure application-wide logging before anything else
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

# Create Flask app
app = Flask(__name__)

# Load configuration
config_class = get_config()
app.config.from_object(config_class)

# Ensure secret key is set
if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
    print("Warning: Using default secret key. Set FLASK_SECRET_KEY in .env for production!")
    if app.config.get('DEBUG'):
        app.config['SECRET_KEY'] = 'dev-secret-key-for-development-only'
    else:
        raise ValueError("FLASK_SECRET_KEY must be set in production environment!")

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = not app.config.get('DEBUG', False)  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = app.config.get('SESSION_TIMEOUT', 3600)

# Create upload folder if it doesn't exist
upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
os.makedirs(upload_folder, exist_ok=True)

# Initialize session manager and register error handlers
from lib.session_manager import session_manager
from lib.error_handlers import register_error_handlers

session_manager.init_app(app)
register_error_handlers(app)


@app.route('/')
def index():
    """Root endpoint - returns basic API info."""
    return jsonify({
        'name': 'Legal Document Filler API',
        'version': '1.0.0-mvp',
        'status': 'operational',
        'endpoints': {
            'upload': '/api/upload',
            'detect': '/api/detect',
            'conversation': '/api/conversation/*',
            'preview': '/api/preview/*',
            'download': '/api/download',
            'health': '/health'
        }
    })


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'ok',
        'service': 'legal-document-filler',
        'version': '1.0.0-mvp'
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found.'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred. Please try again.'
    }), 500


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors."""
    return jsonify({
        'error': 'Bad Request',
        'message': 'Invalid request. Please check your input.'
    }), 400


# Import and register blueprints (routes)
# These will be uncommented as we create the route files
from routes.upload import upload_bp
app.register_blueprint(upload_bp, url_prefix='/api')

from routes.detect import detect_bp
app.register_blueprint(detect_bp, url_prefix='/api')

from routes.conversation import conversation_bp
app.register_blueprint(conversation_bp, url_prefix='/api')

from routes.preview import preview_bp
app.register_blueprint(preview_bp, url_prefix='/api')

from routes.download import download_bp
app.register_blueprint(download_bp, url_prefix='/api')


if __name__ == '__main__':
    # Run the development server
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('DEBUG', True)
    
    print(f"\n🚀 Legal Document Filler MVP")
    print(f"📍 Running on http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"⚙️  Environment: {os.getenv('FLASK_ENV', 'development')}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

