# Tasks for Legal Document Filler MVP

**Source PRD:** `docs/legal-document-filler/requirements-mvp.md`

**Generated:** 2025-11-01

**Target:** 2-day MVP build with Python backend, Gemini 2.5 Pro integration, multi-pattern detection, and HTML preview.

---

## Relevant Files

### Backend Core
- `app.py` - ✅ Main Flask application with initialization, session config, error handlers, health check, upload and detect blueprints registered
- `config.py` - ✅ Configuration management with environment variables, constants, and multi-environment support
- `requirements.txt` - ✅ Python dependencies with flexible version specifications
- `.env.example` - ✅ Example environment variables file with all configuration placeholders
- `.env` - Actual environment variables (gitignored)
- `.gitignore` - ✅ Git ignore patterns for Python, IDE, uploads, and temp files

### Document Processing
- `lib/document_processor.py` - Core document parsing and placeholder detection logic
- `lib/placeholder_detector.py` - ✅ Multi-pattern detection (5 patterns), false positive filtering, normalization, grouping, and summary
- `lib/document_replacer.py` - Run-level placeholder replacement preserving formatting
- `lib/preview_generator.py` - HTML preview generation using mammoth

### LLM Integration
- `lib/llm_service.py` - ✅ Gemini 2.0 Flash with single/batch question generation, LRU caching, rate limiting, toggle control, and fallback handling

### API Routes
- `routes/upload.py` - ✅ File upload endpoint with validation, session management, and cleanup
- `routes/detect.py` - ✅ Placeholder detection endpoint with filtering, status checks, and re-detection
- `routes/conversation.py` - Conversational filling endpoints (next question, submit answer)
- `routes/preview.py` - Preview generation endpoint
- `routes/download.py` - Completed document download endpoint

### Frontend
- `static/index.html` - Main upload page
- `static/conversation.html` - Conversational filling interface page
- `static/preview.html` - Document preview page
- `static/css/styles.css` - Global styles
- `static/js/upload.js` - Upload page JavaScript
- `static/js/conversation.js` - Conversation flow JavaScript
- `static/js/preview.js` - Preview page JavaScript
- `static/js/api.js` - API client utilities

### Utilities
- `lib/session_manager.py` - Session state management and cleanup
- `lib/validators.py` - ✅ File validation (extension, size, MIME type) with comprehensive error handling
- `lib/error_handlers.py` - ✅ Centralized error handling with custom exceptions, .docx validation, and user-friendly messages

### Testing
- `tests/test_placeholder_detector.py` - Unit tests for placeholder detection
- `tests/test_document_replacer.py` - Unit tests for document replacement
- `tests/test_llm_service.py` - Unit tests for LLM integration
- `tests/test_api_routes.py` - Integration tests for API endpoints
- `tests/fixtures/` - Test fixtures (sample .docx files)

### Deployment
- `Procfile` - Process file for deployment (Railway/Render)
- `runtime.txt` - Python version specification
- `README.md` - Setup and deployment instructions

---

## Tasks

- [x] **1.0 Project Setup & Infrastructure**
  - [x] 1.1 Initialize Python project with virtual environment (`python -m venv venv`)
  - [x] 1.2 Create `requirements.txt` with dependencies: `flask>=3.0`, `python-docx>=1.0`, `mammoth>=1.6`, `google-generativeai>=0.3`, `python-dotenv>=1.0`, `werkzeug>=3.0`
  - [x] 1.3 Create `.env.example` with placeholder values: `GOOGLE_API_KEY`, `FLASK_SECRET_KEY`, `SESSION_TIMEOUT`, `MAX_FILE_SIZE_MB`, `ENABLE_LLM`
  - [x] 1.4 Create `.gitignore` to exclude `.env`, `venv/`, `__pycache__/`, `*.pyc`, `uploads/`, `.pytest_cache/`
  - [x] 1.5 Create project directory structure: `lib/`, `routes/`, `static/`, `static/css/`, `static/js/`, `templates/`, `tests/`, `tests/fixtures/`
  - [x] 1.6 Create `config.py` to load environment variables and define constants (file size limits, allowed extensions, session timeout)
  - [x] 1.7 Initialize Git repository and create initial commit
  - [x] 1.8 Install dependencies: `pip install -r requirements.txt`

- [x] **2.0 Backend Core: Document Upload & Multi-Pattern Placeholder Detection**
  - [x] 2.1 Create `app.py` with Flask app initialization, secret key configuration, and session setup
  - [x] 2.2 Implement `lib/validators.py` with functions: `validate_file_extension()`, `validate_file_size()`, `validate_mime_type()`
  - [x] 2.3 Create `routes/upload.py` with POST `/api/upload` endpoint:
    - Accept `.docx` file
    - Validate file type and size (≤5 MB)
    - Save file temporarily with unique session ID
    - Store file path in session
    - Return JSON: `{success: true, session_id: "...", filename: "..."}`
  - [x] 2.4 Implement `lib/placeholder_detector.py` with `detect_placeholders()` function:
    - Define 5 regex patterns: `{{name}}`, `{name}`, `[Name]`, `_____`, `$[_____]`
    - Parse document paragraphs using `python-docx`
    - Extract all matches with original patterns
    - Normalize placeholder names (lowercase, replace spaces with underscores)
    - Return dict: `{normalized_name: [original_patterns]}`
  - [x] 2.5 Implement `reduce_false_positives()` in `lib/placeholder_detector.py`:
    - Filter out numeric citations like `[1]`, `[2(a)]`
    - Filter out "section" references
    - Filter out single-character brackets
    - Keep placeholders with 2+ occurrences or multi-word names
  - [x] 2.6 Create `routes/detect.py` with POST `/api/detect` endpoint:
    - Retrieve uploaded file from session
    - Call `detect_placeholders()` and `reduce_false_positives()`
    - Store detected placeholders in session
    - Return JSON: `{placeholders: {...}, total_unique: 5, total_occurrences: 12}`
  - [x] 2.7 Add error handling for malformed `.docx` files with user-friendly messages

- [x] **3.0 LLM Integration with Google Gemini 2.5 Pro**
  - [x] 3.1 Create `lib/llm_service.py` with Gemini API initialization using `GOOGLE_API_KEY`
  - [x] 3.2 Implement `generate_question(placeholder_name, use_llm=True)` function:
    - Use `@lru_cache` decorator for caching (maxsize=100)
    - Create prompt: "Convert this placeholder name into a clear, professional question for a legal document..."
    - Call `model.generate_content()` with temperature=0.3, max_tokens=50, timeout=3s
    - Return generated question or fallback to "Please provide: {placeholder_name}"
    - Handle exceptions gracefully (timeout, API errors)
  - [x] 3.3 Implement `generate_questions_batch(placeholder_names)` function:
    - Accept list of placeholder names
    - Generate single prompt with numbered placeholders
    - Parse numbered response and map to placeholder names
    - Return dict: `{placeholder_name: question}`
    - Fallback to simple prompts on error
  - [x] 3.4 Add LLM toggle logic: check `ENABLE_LLM` env var and session preference
  - [x] 3.5 Implement rate limiting protection (15 requests/min for free tier)
  - [x] 3.6 Add comprehensive error logging for LLM failures

- [x] **4.0 Frontend: Upload UI & Conversational Interface**
  - [x] 4.1 Create `static/index.html` upload page:
    - File input for `.docx` upload with drag-and-drop support
    - Upload button
    - Loading spinner during upload/parsing
    - Display detected placeholders count
    - "Start Filling" button to begin conversation
  - [x] 4.2 Create `static/js/upload.js`:
    - Handle file selection and validation (client-side)
    - POST file to `/api/upload` endpoint
    - On success, POST to `/api/detect` to get placeholders
    - Display placeholder summary
    - Redirect to conversation page on "Start Filling"
  - [x] 4.3 Create `static/conversation.html`:
    - Progress bar showing "X of Y completed"
    - Question display area (LLM-generated or fallback)
    - Text input for answer with validation (non-empty)
    - "Next" button (disabled until input valid)
    - "Back" button to edit previous answers (if time permits)
    - LLM toggle switch: "Use simple prompts instead ☐"
  - [x] 4.4 Create `routes/conversation.py` with endpoints:
    - GET `/api/conversation/next` - Get next placeholder question (calls LLM or uses fallback)
    - POST `/api/conversation/answer` - Submit answer for current placeholder, store in session
    - GET `/api/conversation/status` - Get progress (filled/total)
  - [x] 4.5 Create `static/js/conversation.js`:
    - Fetch next question on page load
    - Validate input (non-empty)
    - Submit answer on "Next" click
    - Update progress bar
    - Handle LLM toggle state changes
    - Redirect to preview when all placeholders filled
  - [x] 4.6 Create `static/css/styles.css`:
    - Clean, professional styling
    - Responsive layout (desktop-first, mobile-friendly if time permits)
    - Loading states and transitions
    - Progress bar styling
  - [x] 4.7 Add API client utilities in `static/js/api.js`:
    - Helper functions for fetch requests with error handling
    - Session management helpers
    - Loading state management

- [x] **5.0 Document Preview (HTML) & Download**
  - [x] 5.1 Implement `lib/document_replacer.py` with `replace_placeholders()` function:
    - Load document using `python-docx`
    - Iterate through paragraphs and runs (preserve formatting)
    - For each placeholder pattern type, replace with user value
    - Handle all 5 pattern types: `{{}}`, `{}`, `[]`, `___`, `$[___]`
    - Save completed document to temporary location
    - Return path to completed document
  - [x] 5.2 Implement `lib/preview_generator.py` with `generate_preview_html()` function:
    - Use `mammoth` library to convert `.docx` to HTML
    - Wrap HTML in styled template with basic CSS
    - Return complete HTML string
    - Handle conversion errors gracefully
  - [x] 5.3 Create `routes/preview.py` with endpoints:
    - POST `/api/preview/generate` - Generate completed document and HTML preview
    - GET `/api/preview/html` - Serve HTML preview content
  - [x] 5.4 Create `static/preview.html`:
    - Iframe or div to display HTML preview
    - Zoom controls (optional)
    - "Edit Values" button (returns to conversation)
    - "Download .docx" button
  - [x] 5.5 Create `static/js/preview.js`:
    - Fetch and render HTML preview on page load
    - Handle download button click
    - Handle edit button (clear session or navigate back)
  - [x] 5.6 Create `routes/download.py` with GET `/api/download` endpoint:
    - Retrieve completed document from session/temp storage
    - Set appropriate headers for file download
    - Filename format: `{original_name}_completed_{timestamp}.docx`
    - Clean up temporary file after download
    - Return file as attachment

- [ ] **6.0 Session Management, Error Handling & Testing**
  - [ ] 6.1 Implement `lib/session_manager.py`:
    - Function to initialize session with unique ID
    - Function to store file path, placeholders, answers in session
    - Function to check session timeout (60 min inactivity)
    - Function to clear/purge session data
    - Background cleanup task to remove expired sessions
  - [ ] 6.2 Create `lib/error_handlers.py`:
    - Custom error classes: `FileValidationError`, `ParsingError`, `LLMError`, `SessionExpiredError`
    - Flask error handlers for 400, 404, 500 status codes
    - User-friendly error messages for each error type
    - Error logging to console/file
  - [ ] 6.3 Implement session timeout middleware in `app.py`:
    - Check last activity timestamp on each request
    - Redirect to home with message if session expired
  - [ ] 6.4 Add file cleanup logic:
    - Delete uploaded files after session ends
    - Delete generated documents after download
    - Schedule periodic cleanup of orphaned files
  - [ ] 6.5 Create test fixtures in `tests/fixtures/`:
    - Sample `.docx` with various placeholder patterns
    - Sample `.docx` with false positives (citations)
    - Sample `.docx` with mixed-case brackets like `[Date of Safe]`
  - [ ] 6.6 Write unit tests in `tests/test_placeholder_detector.py`:
    - Test all 5 pattern types detected correctly
    - Test normalization (case-insensitive, space → underscore)
    - Test false positive filtering (citations, sections)
    - Test mixed-case bracket detection: `[Date of Safe]`
  - [ ] 6.7 Write unit tests in `tests/test_document_replacer.py`:
    - Test replacement preserves formatting (bold, italic)
    - Test all pattern types replaced correctly
    - Test run-level replacement (not paragraph-level)
  - [ ] 6.8 Write unit tests in `tests/test_llm_service.py`:
    - Test question generation with mocked Gemini API
    - Test fallback behavior on timeout/error
    - Test caching (same placeholder = cached response)
    - Test batch generation
  - [ ] 6.9 Write integration tests in `tests/test_api_routes.py`:
    - Test full flow: upload → detect → answer → preview → download
    - Test file validation errors
    - Test session expiration
    - Test LLM toggle on/off
  - [ ] 6.10 Add logging throughout application (request IDs, errors, performance metrics)

- [ ] **7.0 Deployment & Production Readiness**
  - [ ] 7.1 Create `README.md` with:
    - Project description and features
    - Setup instructions (venv, dependencies, environment variables)
    - How to get Gemini API key (https://aistudio.google.com/app/apikey)
    - Local development instructions (`python app.py`)
    - Testing instructions
    - Deployment guide
  - [ ] 7.2 Create `Procfile` for Railway/Render: `web: gunicorn app:app`
  - [ ] 7.3 Add `gunicorn>=21.0` to `requirements.txt` for production server
  - [ ] 7.4 Create `runtime.txt` specifying Python version: `python-3.10` or `python-3.11`
  - [ ] 7.5 Set up environment variables on deployment platform:
    - `GOOGLE_API_KEY` - Gemini API key
    - `FLASK_SECRET_KEY` - Random secret key for sessions
    - `SESSION_TIMEOUT=3600`
    - `MAX_FILE_SIZE_MB=5`
    - `ENABLE_LLM=true`
  - [ ] 7.6 Configure HTTPS on Railway/Render (automatic with platform)
  - [ ] 7.7 Test deployed application end-to-end:
    - Upload various legal document templates
    - Test multi-pattern detection with real documents
    - Test LLM question quality
    - Test preview rendering
    - Test download
  - [ ] 7.8 Implement basic rate limiting (10 uploads/hour per IP) using Flask-Limiter
  - [ ] 7.9 Add health check endpoint: GET `/health` returns `{status: "ok"}`
  - [ ] 7.10 Monitor initial usage and fix any deployment-specific bugs
  - [ ] 7.11 Document known limitations in README (body text only, no tables/headers)

---

## Notes

### Dependency Versioning
- Use flexible version specifications (e.g., `>=3.0` instead of `==3.0.0`) to avoid compatibility issues
- This allows pip to install compatible newer versions automatically
- Example `requirements.txt`:
```txt
flask>=3.0
python-docx>=1.0
mammoth>=1.6
google-generativeai>=0.3
python-dotenv>=1.0
werkzeug>=3.0
gunicorn>=21.0
pytest>=7.0  # for testing
```

### Testing Commands
- Run all tests: `pytest tests/`
- Run specific test file: `pytest tests/test_placeholder_detector.py`
- Run with coverage: `pytest --cov=lib tests/`

### Local Development
```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Run
python app.py
# Visit http://localhost:5000
```

### Priority Guidelines
If time is running short, prioritize in this order:
1. **Must Have**: Tasks 1.0, 2.0, 4.0 (basic flow without LLM)
2. **High Priority**: Task 5.0 (preview and download)
3. **Medium Priority**: Task 3.0 (LLM integration - can work with fallback only)
4. **Lower Priority**: Task 6.0 (comprehensive testing - do basic smoke tests)
5. **Can Defer**: Advanced error handling, "Back" button, mobile responsiveness

### Key Implementation Tips
- **Multi-pattern regex**: Use `r'\[([A-Z][a-zA-Z0-9_\s]+)\]'` to catch `[Date of Safe]`, `[NAME]`, etc.
- **Run-level replacement**: Iterate `paragraph.runs` not `paragraph.text` to preserve formatting
- **Gemini caching**: Use `@lru_cache` decorator to avoid repeated API calls for same placeholder
- **Session security**: Use `secrets.token_hex(16)` for Flask secret key
- **File cleanup**: Use `atexit` or background scheduler for orphaned file cleanup

### Potential Gotchas
- `python-docx` doesn't preserve all formatting (images, text boxes) - document this limitation
- `mammoth` HTML conversion loses some styles - good enough for text verification
- Gemini free tier has 15 RPM limit - implement request throttling or use batch generation
- Square bracket patterns need careful false positive filtering - test with real legal docs

