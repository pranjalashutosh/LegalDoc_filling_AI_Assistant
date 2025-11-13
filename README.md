# Lexsy - Legal Document Filler

A Flask-based web application that automatically detects and fills placeholders in legal documents using AI.

## Features

- **Intelligent Placeholder Detection**: Automatically identifies placeholders in legal documents using hybrid detection (LLM + pattern matching)
- **Interactive Document Filling**: Web-based interface for filling in document fields through conversation
- **Document Preview**: Preview filled documents before downloading
- **Multiple Format Support**: Works with DOCX files
- **Session Management**: Handles multiple user sessions securely

## Tech Stack

- **Backend**: Flask (Python)
- **AI/LLM**: Google Generative AI (Gemini)
- **Document Processing**: python-docx, mammoth
- **Frontend**: HTML, CSS, JavaScript
- **Testing**: pytest

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/lexsy-2.git
cd lexsy-2
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- **Windows**: `venv\Scripts\activate`
- **Mac/Linux**: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a `.env` file in the root directory with your API keys:
```
GOOGLE_API_KEY=your_google_api_key_here
```

6. Run the application:
```bash
python app.py
```

7. Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
lexsy-2/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── lib/                  # Core library modules
│   ├── document_replacer.py
│   ├── llm_service.py
│   ├── placeholder_detector.py
│   └── ...
├── routes/               # API route handlers
├── static/              # Frontend files (HTML, CSS, JS)
├── tests/               # Unit tests
├── templates/           # Flask templates
└── requirements.txt     # Python dependencies
```

## Usage

1. Upload a legal document (DOCX format)
2. The system will automatically detect placeholders
3. Fill in the required information through the interactive conversation
4. Preview your filled document
5. Download the completed document

## Testing

Run the test suite:
```bash
pytest
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines if applicable]

## Contact

[Add your contact information]

