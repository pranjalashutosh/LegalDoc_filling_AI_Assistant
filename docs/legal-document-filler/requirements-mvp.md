# Legal Document Filler – MVP Requirements (2-Day Build)

## 1. Scope & Goals
- Build a **public web app** that accepts `.docx` uploads, detects multiple placeholder patterns, guides users through an AI-enhanced conversational interface to fill values, provides an in-browser preview, and allows download of the completed document.
- **Deadline**: 2 days. Core features: upload → multi-pattern detection → LLM-enhanced filling → HTML preview → download.
- **Key Differentiators**: 
  - Multiple placeholder patterns (not just `{{}}`)
  - AI-generated natural language questions (with fallback)
  - In-browser document preview before download
- **Philosophy**: Functional MVP with intelligent UX. Focus on working end-to-end flow with smart features that demonstrate value.

## 2. Core Assumptions
- **Anonymous sessions** (no authentication required)
- **Python backend** (Flask/FastAPI) with simple frontend (vanilla JS or lightweight framework)
- **LLM integration**: Google Gemini 2.5 Pro API with graceful fallback
- **In-memory session storage** (Redis optional or server-side sessions)
- **Public HTTPS deployment** (single instance via Render, Railway, or similar free tier)
- **File limits**: ≤5 MB, ≤50 pages for MVP
- **Ephemeral data**: Files and user inputs auto-purge after session timeout (~1 hour of inactivity)
- **Internet connection required**: For LLM API calls (works offline with LLM disabled)

## 3. Glossary
- **Template Text**: Static legal content that remains unchanged
- **Placeholder**: Dynamic field requiring user input (e.g., `{{client_name}}`)
- **Conversational Interface**: Simple chat-style form to collect placeholder values
- **Completed Document**: `.docx` with all placeholders replaced by user-provided values

---

## 4. Functional Requirements (MVP Core)

### FR-1: Document Upload
**Must Have:**
- Web page with file upload input accepting `.docx` files only
- Validate file extension and MIME type before processing
- Display clear error message if file is invalid or too large
- Store uploaded file temporarily in session

**Acceptance Criteria:**
- ✅ User can access public URL
- ✅ `.docx` file uploads successfully
- ✅ Non-`.docx` files are rejected with user-friendly error
- ✅ File is accessible during session for processing

---

### FR-2: Placeholder Detection (Multiple Patterns)
**Must Have:**
- Parse document body text (paragraphs and runs) for placeholders
- Detect **multiple placeholder patterns**:
  - `{{placeholder_name}}` - Double curly braces
  - `[Placeholder Name]` - Square brackets (any case: `[DATE]`, `[Date of Safe]`, `[COMPANY NAME]`)
  - `{placeholder_name}` - Single curly braces
  - `_____________` - Underscores/fill-in-the-blank patterns (detect sequences of 5+ underscores)
  - `$[_____________]` - Dollar sign with brackets and underscores
- Smart heuristics to reduce false positives:
  - Ignore legal citations like `[1]`, `[Section 2(b)]`, `[2(a)]` (numeric or section reference patterns)
  - Treat `[Word]` as placeholder if: contains 2+ words OR contains uppercase letters OR repeated 2+ times in document
  - Ignore single-character brackets like `[a]`, `[x]`
  - Label context clearly (e.g., "Name:", "Address:", "Email:") preceding underscores
- Extract list of unique placeholders (case-insensitive, deduplicated)
- Normalize variations (e.g., `[Date of Safe]`, `[DATE OF SAFE]`, `{{date_of_safe}}` → `date_of_safe`)
- Display count of detected placeholders to user

**Acceptance Criteria:**
- ✅ Detects all pattern types: `{{}}`, `[]`, `{}`, `___`, `$[___]`
- ✅ Detects mixed-case square brackets: `[Date of Safe]`, `[COMPANY NAME]`, `[Client Name]`
- ✅ Shows unique normalized list (e.g., `[Date of Safe]` → `date_of_safe`)
- ✅ Displays total count (e.g., "Found 8 unique placeholders across 15 locations")
- ✅ Handles documents with no placeholders gracefully
- ✅ False positive rate <10% for square bracket patterns (ignores citations)

**Nice-to-Have (if time permits):**
- Context label extraction (capture "Name:", "Email:" prefixes)
- Pattern priority configuration (prefer `{{}}` over `[]` if ambiguous)

**Out of Scope (Phase 2):**
- Headers, footers, tables (focus on body text only)
- Complex grouping/normalization beyond case-insensitivity

---

### FR-3: Conversational Filling (with LLM Integration)
**Must Have:**
- Chat-style interface presenting one placeholder at a time
- **LLM-enhanced question generation**: Use AI to rephrase placeholder names into natural questions
  - Example: `client_name` → "What is the client's full legal name?"
  - Example: `signing_date` → "When will this document be signed? (Please provide a date)"
  - Fallback to rule-based prompts if LLM fails/times out
- Show placeholder name clearly with context-aware hints
- Text input for each value with basic validation (non-empty)
- "Next" button to proceed to next placeholder
- Progress indicator (e.g., "3 of 8 completed")
- Toggle to disable LLM and use simple prompts (for debugging or preference)

**LLM Integration Details:**
- **API**: Google Gemini 2.5 Pro (fast, cost-effective, high-quality output)
- **Prompt template**: "Convert this placeholder name into a clear, professional question for a legal document: {placeholder_name}"
- **Timeout**: 3 seconds max; fallback to "Please provide: {placeholder_name}"
- **Privacy**: Only send placeholder name (not document content or user data)
- **Caching**: Cache LLM responses per placeholder to avoid repeat API calls
- **Model**: `gemini-2.5-pro` via Google Generative AI SDK

**Acceptance Criteria:**
- ✅ User steps through each placeholder sequentially
- ✅ LLM generates natural language questions for each placeholder
- ✅ Fallback to simple prompts works when LLM unavailable
- ✅ Cannot submit empty values
- ✅ Progress is visible throughout flow
- ✅ All values are collected before proceeding to preview/download
- ✅ Toggle switch to enable/disable LLM phrasing works

**Nice-to-Have (if time permits):**
- Back button to edit previous values
- Basic type detection (text, date, number) with simple validation
- Context snippets from document displayed alongside question

**Out of Scope (Phase 2):**
- Jump to specific field
- Skip functionality
- Advanced validation (email regex, phone formats, currency)
- Multi-turn LLM conversations or clarification dialogs

---

### FR-4: Document Generation, Preview & Download
**Must Have:**
- Replace all placeholder patterns with user-provided values (respecting original pattern format)
- Preserve basic formatting (font, bold, italic, paragraph structure)
- **On-page preview before download**: Render completed document for user verification
  - Convert `.docx` to HTML or PDF for in-browser display
  - Show side-by-side or full-page preview with zoom controls
  - Highlight replaced fields (optional but nice visual feedback)
- Generate downloadable `.docx` file after preview approval
- Filename format: `{original_name}_completed_{timestamp}.docx`
- Allow user to go back and edit values if preview reveals issues

**Preview Implementation Options:**
1. **HTML Preview** (Recommended for MVP):
   - Use `mammoth.js` or Python `mammoth` to convert `.docx` → HTML
   - Render HTML in iframe or div with basic styling
   - Faster, works client-side or server-side
   - Good enough for text verification

2. **PDF Preview** (Alternative):
   - Convert `.docx` → PDF using `docx2pdf` or LibreOffice headless
   - Embed PDF viewer (e.g., PDF.js)
   - Higher fidelity but slower generation

**Acceptance Criteria:**
- ✅ All placeholders are replaced with correct values
- ✅ Preview displays completed document content clearly
- ✅ User can review preview before downloading
- ✅ "Edit" button allows returning to change values
- ✅ "Download" button triggers `.docx` file download
- ✅ File downloads successfully after preview approval
- ✅ File opens in Microsoft Word/Google Docs without errors
- ✅ Basic text formatting is preserved in final document

**Nice-to-Have (if time permits):**
- Visual diff showing what changed (original vs filled)
- Print preview option
- Export as PDF option

**Out of Scope (Phase 2):**
- Tables, headers, footers preservation (body text focus)
- Images, hyperlinks, complex styles
- In-browser editing of completed document (must re-enter via conversation flow)

---

### FR-5: Session Management
**Must Have:**
- Maintain uploaded file and collected answers during active session
- Clear session data on timeout (60 minutes of inactivity)
- Allow user to restart/clear session manually

**Acceptance Criteria:**
- ✅ User can complete flow without data loss during session
- ✅ Inactive sessions are cleaned up automatically
- ✅ User can reset and upload a new document

**Out of Scope (Phase 2):**
- Persistence across browser refresh
- Multiple document management
- Session recovery after timeout

---

### FR-6: Error Handling
**Must Have:**
- User-friendly error messages for:
  - Invalid file upload
  - Parsing failures
  - Generation errors
- Allow retry/re-upload on error

**Acceptance Criteria:**
- ✅ Errors display clear, actionable messages
- ✅ User can recover from errors without restarting application
- ✅ Server logs capture errors for debugging

---

## 5. Non-Functional Requirements (MVP)

### Performance
- Upload + parsing: ≤3 seconds for typical 1-2 MB document
- Multi-pattern detection: ≤2 seconds for 50-page document
- LLM question generation: ≤3 seconds per placeholder (with 3s timeout + fallback)
- Document generation: ≤2 seconds
- Preview rendering (HTML): ≤3 seconds
- Chat interactions (non-LLM): ≤300ms response time

### Security & Privacy
- **HTTPS only** (enforce TLS)
- **No permanent storage** of uploaded documents or user data
- **Files purged automatically** after session timeout (60 min)
- **LLM privacy**: Only placeholder names sent to Google Gemini (never document content or PII)
- **API key security**: Environment variables only; never hardcoded or committed
- **No third-party data sharing** beyond LLM API calls to Google (documented in privacy policy)
- **Rate limiting**: Basic protection against abuse (10 uploads/hour per IP)
- **Google API compliance**: Data sent to Gemini API subject to Google's terms; no data retention for free tier

### Reliability
- LLM fallback: If API fails, gracefully degrade to simple prompts (no blocking errors)
- Error recovery: All errors allow retry without restarting full flow
- Session resilience: Maintain state during active session (within timeout window)

### Compatibility
- Browser support: Latest Chrome, Edge, Firefox, Safari
- Desktop-first (mobile-responsive design is nice-to-have)
- Document support: `.docx` files created in Word 2016+ or Google Docs

### Deployment
- Single instance deployment on free/low-cost platform (Railway/Render)
- Accessible via public HTTPS URL
- Minimal infrastructure (no complex orchestration)
- Environment variables for configuration (API keys, session timeout)

### Cost Constraints
- **LLM usage**: Free tier (Gemini 2.5 Pro: 15 requests/min, 1,500 requests/day)
- **Infrastructure**: Free tier (Railway/Render) or <$10/month
- **Total MVP budget**: ~$0-10 (essentially free with Gemini free tier)

---

## 6. Technical Implementation Guide

### Technology Stack (Recommended)
**Backend:**
- Python 3.10+
- **Flask** or **FastAPI** (lightweight, fast setup)
- **python-docx** library for `.docx` parsing and generation
- **mammoth** library for `.docx` → HTML preview conversion
- **google-generativeai** SDK for LLM integration (Gemini 2.5 Pro)
- **Redis** (optional) or Flask sessions for state management

**Frontend:**
- Vanilla JavaScript + HTML/CSS (no framework overhead)
- OR lightweight: **Alpine.js**, **htmx**, or **Svelte** (if familiar)
- **PDF.js** (optional, if using PDF preview instead of HTML)

**LLM API:**
- **Google Gemini 2.5 Pro** (excellent quality, cost-effective, fast)
- Free tier: 15 requests per minute, generous quota
- Environment variable for API key management

**Deployment:**
- **Railway**, **Render**, or **Fly.io** (free tier with HTTPS)
- Docker optional but not required
- Environment variables for LLM API keys

### Dependencies & Installation

**Python Requirements (`requirements.txt`):**
```txt
flask>=3.0
python-docx>=1.0
mammoth>=1.6
google-generativeai>=0.3
python-dotenv>=1.0
werkzeug>=3.0
gunicorn>=21.0
```

**Environment Variables (`.env`):**
```bash
GOOGLE_API_KEY=your-gemini-api-key-here
FLASK_SECRET_KEY=your-random-secret-key
SESSION_TIMEOUT=3600  # 1 hour in seconds
MAX_FILE_SIZE_MB=5
ENABLE_LLM=true  # Set to false to disable LLM by default
```

**Setup Commands:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
# Get your API key from: https://aistudio.google.com/app/apikey

# Run locally
python app.py
```

---

### Placeholder Detection Logic (Multiple Patterns)
```python
import re
from docx import Document

def detect_placeholders(docx_path):
    doc = Document(docx_path)
    placeholders = {}  # {normalized_name: [original_patterns]}
    
    # Define patterns
    patterns = [
        (r'\{\{([a-zA-Z0-9_]+)\}\}', 'double_curly'),           # {{name}}
        (r'\{([a-zA-Z0-9_]+)\}', 'single_curly'),               # {name}
        (r'\[([A-Z][a-zA-Z0-9_\s]+)\]', 'square_bracket'),      # [Date of Safe], [NAME], [COMPANY NAME]
        (r'_{5,}', 'underscore'),                               # _____
        (r'\$\[_{5,}\]', 'dollar_underscore'),                  # $[_____]
    ]
    
    for paragraph in doc.paragraphs:
        text = paragraph.text
        for pattern, pattern_type in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                original = match.group(0)
                # Normalize placeholder name
                if pattern_type == 'underscore':
                    # Try to extract label before underscores
                    label_match = re.search(r'(\w+):\s*_+', text[:match.start()])
                    normalized = label_match.group(1).lower() if label_match else f"field_{len(placeholders)}"
                elif pattern_type == 'dollar_underscore':
                    # Try to find label or use generic name
                    normalized = f"amount_{len(placeholders)}"
                else:
                    # For other patterns, normalize the captured content
                    normalized = match.group(1).lower().replace(' ', '_')
                
                if normalized not in placeholders:
                    placeholders[normalized] = []
                placeholders[normalized].append(original)
    
    return placeholders

def reduce_false_positives(placeholders, doc_text):
    """Remove likely false positives like [1], [2(a)], or [Section 2(b)]"""
    filtered = {}
    for name, originals in placeholders.items():
        # Skip if looks like numeric citation
        if name.isdigit():
            continue
        # Skip if contains "section" keyword (legal references)
        if 'section' in name.lower():
            continue
        # Skip if single character (like [a], [x])
        if len(name) == 1:
            continue
        # Skip if looks like subsection notation (contains parentheses patterns)
        if any(re.match(r'\d+\([a-z]\)', orig) for orig in originals):
            continue
        # Keep if it has multiple words or appears multiple times
        if len(originals) >= 2 or '_' in name or len(name) > 3:
            filtered[name] = originals
    
    return filtered
```

### Replacement Logic (Run-Level)
```python
def replace_placeholders(docx_path, values_dict, output_path):
    doc = Document(docx_path)
    
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            # Replace in runs to preserve formatting
            for key, value in values_dict.items():
                # Handle all pattern types
                patterns_to_replace = [
                    f'{{{{{key}}}}}',     # {{key}}
                    f'{{{key}}}',         # {key}
                    f'[{key.upper()}]',   # [KEY]
                    f'[{key.replace("_", " ").title()}]',  # [Key Name]
                ]
                for pattern in patterns_to_replace:
                    if pattern in run.text:
                        run.text = run.text.replace(pattern, value)
    
    doc.save(output_path)
```

### LLM Integration for Question Generation (Gemini 2.5 Pro)
```python
import google.generativeai as genai
import os
from functools import lru_cache

# Configure Gemini API
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-pro')

@lru_cache(maxsize=100)
def generate_question(placeholder_name, use_llm=True):
    """Generate natural language question for placeholder using Gemini 2.5 Pro"""
    
    # Fallback question
    fallback = f"Please provide: {placeholder_name.replace('_', ' ')}"
    
    if not use_llm:
        return fallback
    
    try:
        prompt = f"""Convert this placeholder name into a clear, professional question for a legal document.
Keep it concise (one sentence) and professional.

Placeholder: {placeholder_name}

Question:"""
        
        # Generate with timeout
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.3,  # More consistent, less creative
                'max_output_tokens': 50,
                'top_p': 0.8,
            },
            request_options={'timeout': 3}
        )
        
        question = response.text.strip()
        return question if question else fallback
        
    except Exception as e:
        print(f"Gemini API failed: {e}, using fallback")
        return fallback

# Alternative: Batch generate questions for all placeholders at once
def generate_questions_batch(placeholder_names):
    """Generate questions for multiple placeholders in one API call (more efficient)"""
    
    if not placeholder_names:
        return {}
    
    try:
        placeholders_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(placeholder_names)])
        prompt = f"""Convert these placeholder names into clear, professional questions for a legal document.
Return only the questions, numbered to match the input.

Placeholders:
{placeholders_list}

Questions:"""
        
        response = model.generate_content(prompt, generation_config={'temperature': 0.3})
        
        # Parse response (simple line-based parsing)
        lines = response.text.strip().split('\n')
        questions = {}
        for i, name in enumerate(placeholder_names):
            if i < len(lines):
                # Remove numbering if present
                question = lines[i].lstrip('0123456789. ')
                questions[name] = question
            else:
                questions[name] = f"Please provide: {name.replace('_', ' ')}"
        
        return questions
        
    except Exception as e:
        print(f"Batch generation failed: {e}")
        # Fallback: generate simple questions
        return {name: f"Please provide: {name.replace('_', ' ')}" for name in placeholder_names}
```

### Preview Generation (HTML)
```python
import mammoth

def generate_preview_html(docx_path):
    """Convert .docx to HTML for preview"""
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value  # The generated HTML
        messages = result.messages  # Any messages (warnings, errors)
    
    # Wrap in basic styling
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: auto; }}
            p {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    return styled_html
```

---

## 7. User Flow (Happy Path)

```
1. User visits public URL
   ↓
2. User uploads .docx file (e.g., SAFE agreement template)
   ↓
3. System parses and displays: "Found 5 unique placeholders (12 total occurrences)"
   → Shows detected patterns: 
      • {{company_name}}
      • [Date of Safe] 
      • [INVESTOR NAME]
      • {purchase_amount}
      • Name:_____
   ↓
4. User clicks "Start Filling"
   ↓
5. System shows Gemini-generated question:
   "What is the legal name of the company issuing this SAFE?" (1 of 5)
   [Toggle: Use simple prompts instead ☐]
   ↓
6. User enters value, clicks "Next"
   ↓
7. Repeat until all 5 values collected
   → Progress bar shows: 5 of 5 completed ✓
   ↓
8. System generates completed document and preview
   ↓
9. Preview displays in-browser (HTML rendering via Mammoth)
   → User reviews: all placeholders replaced correctly
   [Edit Values] [Download .docx]
   ↓
10. User clicks "Download" → receives completed .docx
```

---

## 8. Out of Scope (Deferred to Phase 2)

The following features are **explicitly excluded** from the 2-day MVP:

- ❌ Advanced type inference and validation (email regex, phone formats, currency locale)
- ❌ Headers, footers, tables, images support (focus on body text only)
- ❌ Session persistence across browser refresh
- ❌ Mobile-optimized UI (desktop-first approach)
- ❌ Accessibility features (WCAG compliance)
- ❌ User accounts or authentication
- ❌ Batch processing (multiple documents at once)
- ❌ Configuration/settings panel (except LLM toggle)
- ❌ Advanced error recovery (complex retry logic)
- ❌ Context-aware field suggestions based on document type
- ❌ Multi-language support
- ❌ Audit trails or version history
- ❌ Advanced formatting preservation (text boxes, shapes, charts)

---

## 9. Success Criteria (Demo Checklist)

MVP is considered **complete** when:

- [ ] Public URL is accessible via HTTPS
- [ ] User can upload a `.docx` file successfully
- [ ] System detects **multiple placeholder patterns**: `{{}}`, `[]`, `{}`, `___`, `$[___]`
- [ ] System normalizes and deduplicates placeholders correctly
- [ ] **LLM generates natural questions** for each placeholder (with fallback working)
- [ ] User can fill all placeholders via conversational UI with LLM-enhanced prompts
- [ ] Progress indicator shows completion status
- [ ] **Preview displays completed document** (HTML or PDF rendering)
- [ ] User can review preview and go back to edit values
- [ ] Downloaded `.docx` file opens in Word with all placeholders replaced
- [ ] Basic formatting (bold, italic, fonts) is preserved
- [ ] Session clears after timeout
- [ ] Basic error messages display for invalid uploads
- [ ] LLM toggle switch works (enable/disable AI phrasing)

---

## 10. Development Timeline (48 Hours)

### Day 1 (Hours 0-24)
**Morning (0-4h):**
- Project setup: Python environment, Flask/FastAPI skeleton
- Install dependencies: `python-docx`, `mammoth`, `openai`, `flask`/`fastapi`
- File upload endpoint with validation
- Basic frontend with upload form

**Afternoon (4-9h):**
- **Implement multi-pattern placeholder detection** (5h)
  - Regex patterns for: `{{}}`, `{}`, `[]`, `___`, `$[___]`
  - False positive filtering (citations, single chars)
  - Normalization and deduplication logic
- Display detected placeholders on frontend with counts
- Session storage for uploaded file and state

**Evening (9-15h):**
- **LLM integration** (3h)
  - OpenAI API setup with environment variables
  - Question generation function with caching
  - Fallback logic and timeout handling
- **Build conversational UI** (3h)
  - Sequential form with LLM-generated questions
  - LLM toggle switch
  - Progress tracking
- Connect frontend to backend API

**Night (15-20h):**
- **Implement placeholder replacement logic** (2h)
  - Run-level replacement to preserve formatting
  - Handle all pattern types
- **Preview generation** (3h)
  - Integrate `mammoth` for .docx → HTML conversion
  - Create preview page with styling
  - Edit/download buttons
- Basic testing with sample documents

### Day 2 (Hours 20-48)
**Morning (20-26h):**
- **Testing and refinement** (6h)
  - Test multiple pattern detection with real legal docs
  - Test LLM question generation quality
  - Test preview rendering fidelity
  - Fix bugs and edge cases

**Afternoon (26-32h):**
- **Error handling and validation** (3h)
  - User-friendly error messages
  - Session timeout logic
  - Retry mechanisms
- **UI polish** (3h)
  - Responsive layout adjustments
  - Loading states for LLM calls
  - Preview zoom/scroll controls

**Evening (32-40h):**
- **Deployment** (4h)
  - Setup Railway/Render account
  - Configure environment variables (OpenAI API key)
  - HTTPS configuration
  - Deploy and test on production URL
- **End-to-end testing** (4h)
  - Test full flow on deployed instance
  - Performance testing
  - Cross-browser testing

**Final Hours (40-48h):**
- **Final polish and documentation** (4h)
  - Bug fixes from deployment testing
  - Write README with setup instructions
  - Document LLM usage and costs
- **Testing with diverse documents** (2h)
  - Test with different legal document types
  - Edge case validation
- **Buffer time** (2h)
  - Unexpected issues
  - Last-minute improvements

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Multiple patterns create false positives** | Implement strict heuristics; test with 5+ real legal docs; allow manual override |
| **LLM API costs exceed budget** | Use Gemini 2.5 Pro (generous free tier: 15 RPM); cache all responses; batch generation |
| **LLM latency slows UX** | 3s timeout with immediate fallback; pre-generate questions in batch on upload |
| **Preview rendering loses formatting** | Use HTML preview (good enough for text); document limitations clearly |
| **`.docx` parsing edge cases** | Test with 3-5 common legal templates; graceful degradation |
| **Formatting loss on replacement** | Use run-level replacement; test with formatted documents |
| **Deployment complexity** | Use one-click deploy platforms (Railway/Render); avoid custom infrastructure |
| **Time overrun on new features** | Multi-pattern detection = highest priority; Preview = second; LLM = can be simplified/deferred last minute |
| **Google API key exposure** | Use environment variables; never commit keys; rotate if leaked |
| **Gemini rate limits (15 RPM free tier)** | Implement request throttling; use batch generation; cache aggressively |

---

## 12. Phase 2 Roadmap (Post-MVP)

Features to add after successful 2-day MVP demo:

1. **Headers, Footers, Tables**: Extend detection/replacement beyond body text
2. **Advanced Validation**: Email regex, phone formats, date format checking with locale support
3. **Session Persistence**: Maintain state across browser refresh (Redis or database)
4. **Context Snippets**: Display surrounding text for each placeholder during filling
5. **Multi-turn LLM Conversations**: Allow users to ask clarifying questions to AI
6. **PDF Export**: Direct export to PDF (in addition to .docx)
7. **Visual Diff Preview**: Show highlighted changes (original vs filled) in preview
8. **Mobile UI**: Fully responsive mobile-optimized interface
9. **Batch Upload**: Process multiple documents simultaneously
10. **Template Library**: Save and reuse common placeholder mappings
11. **Accessibility**: WCAG 2.1 AA compliance (screen readers, keyboard nav)
12. **User Accounts**: Save session history, favorite templates
13. **Advanced Patterns**: Support for `__name__` pattern, custom regex patterns
14. **Audit Trail**: Track who filled what and when
15. **Multi-language Support**: i18n for UI and document languages


