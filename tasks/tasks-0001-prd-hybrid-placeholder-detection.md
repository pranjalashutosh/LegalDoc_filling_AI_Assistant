## Relevant Files

- `lib/placeholder_detector.py` - Deterministic DOCX placeholder detection; extend patterns and ignore rules; include tables.
- `lib/document_replacer.py` - Applies answers to DOCX; ensure immediate fill semantics align; prep for per-instance overrides.
- `lib/llm_service.py` - Gemini integration; add placeholder validation and question generation with sentence+neighbors context.
- `routes/detect.py` - Detection API; return candidates and store normalized placeholders in session (validate/augment contexts).
- `routes/conversation.py` - Next-question/answer endpoints; integrate LLM validation, radio/check option handling, consolidation.
- `routes/preview.py` - Preview generation; unchanged flow but should reflect immediately stored answers.
- `static/js/upload.js` - Upload and detection UI; LLM toggle; show detected pattern summary.
- `static/js/conversation.js` - One-by-one Q&A; no suggestions; immediate answer persistence; hook for per-instance edits.
- `tests/test_placeholder_detector.py` - Unit tests for deterministic detection patterns and ignore list (to be added).
- `tests/test_llm_service.py` - Extend tests for validation, question generation, caching, and error fallback.
- `tests/test_api_routes.py` - Integration tests across upload → detect → conversation → preview.

### Notes

- Keep DOCX-only scope. Scan body paragraphs and tables; exclude headers/footers/footnotes for detection.
- Always invoke LLM for validation and curated question generation per candidate.
- Provide only the sentence and its immediate neighbors to the LLM.
- English-only prompts; immediate auto-fill behavior is realized by updating session answers and reflecting in preview.
- Consolidate repeated placeholders to one question with reuse; allow per-instance overrides after initial fill.

## Tasks

- [x] 1.0 Update deterministic DOCX detection per PRD (patterns, ignores, body+tables)
  - [x] 1.1 Scan both body paragraphs and table cells in `lib/placeholder_detector.py` for comprehensive detection
  - [x] 1.2 Update underscore rule to "≥3 underscores" for blanks; support `Name:______` and `$[__________]`
  - [x] 1.3 Ensure bracketed tokens detection includes `[TITLE]`, `[title]`, and free-text like `[something written]`
  - [x] 1.4 Add ignore filters: common acronyms (e.g., LLC, USA), section tags (e.g., [Exhibit A]), numeric citations (e.g., [1]), and email template boilerplate
  - [x] 1.5 Emit candidate metadata: normalized key, original text, pattern type, and minimal context (sentence + neighbors)
  - [x] 1.6 Return grouped summary and candidate list with stable instance IDs for later per-instance edits

- [x] 2.0 Add LLM validation + question generation (Gemini 2.5 Pro Preview, sentence+neighbors, radio/check handling)
  - [x] 2.1 Update `lib/llm_service.py` model to Gemini 2.5 Pro Preview and verify env/config
  - [x] 2.2 Implement `validate_candidate(context)` to classify "placeholder or not" using sentence+neighbors
  - [x] 2.3 Implement `generate_question_from_context(context, placeholder_key, options=None)` for curated questions (English-only)
  - [x] 2.4 Add handling for radio/check cases: detect options (e.g., Male/Female) and build a single-select question
  - [x] 2.5 Enforce minimal payload: only sentence + immediate neighbors sent to the LLM
  - [x] 2.6 Add caching and graceful fallback to simple question on errors

- [x] 3.0 Implement consolidation with answer reuse and per-instance override mechanism
  - [x] 3.1 Generate canonical keys to consolidate repeated placeholders (e.g., `client_name`) across variants
  - [x] 3.2 Reuse a single answer for all instances of the same canonical key by default
  - [x] 3.3 Introduce instance IDs and a mapping from canonical key → [instances]
  - [x] 3.4 Add server-side support to override a single instance's value without changing others

- [x] 4.0 Wire detection and conversation APIs to pass context, validate candidates, and persist answers immediately
  - [x] 4.1 In `routes/detect.py`, store candidate list, contexts, and grouped summary in session
  - [x] 4.2 In `routes/conversation.py`, `GET /api/conversation/next` to fetch next validated candidate and return curated question (with options when applicable)
  - [x] 4.3 In `routes/conversation.py`, `POST /api/conversation/answer` to persist answers immediately in session (auto-fill semantics)
  - [x] 4.4 Add endpoint to support per-instance override: accepts instance ID, value; updates session mapping

- [x] 5.0 Update frontend flows for one-by-one Q&A, no suggestions, immediate fill, and per-instance edits
  - [x] 5.1 In `static/js/conversation.js`, support questions with single-select options (radio UI) and plain text answers
  - [x] 5.2 Ensure no suggested answers are displayed; only user-provided input
  - [x] 5.3 Persist each answer immediately to session via API; keep progress indicators
  - [x] 5.4 Add minimal per-instance edit affordance (e.g., selectable instance list or "edit this instance" follow-up)
  - [x] 5.5 Keep preview/download unchanged; ensure preview reflects latest answers

- [x] 6.0 Configure model and safeguards (model name update, context clipping, caching/rate limits)
  - [x] 6.1 Switch model configuration to Gemini 2.5 Pro Preview; document env vars
  - [x] 6.2 Clip context to sentence + neighbors with hard character/token limit
  - [x] 6.3 Extend caching and existing rate-limit checks; add batch-friendly hooks if needed
  - [x] 6.4 Robust logging for LLM usage and fallbacks (no PII in logs)

- [ ] 7.0 Add unit and integration tests for detection, LLM validation, APIs, and flows
  - [ ] 7.1 Create `tests/test_placeholder_detector.py` covering patterns, ignores, and tables-only scope
  - [ ] 7.2 Extend `tests/test_llm_service.py` for validation/classification, question generation, radio options, and fallbacks
  - [ ] 7.3 Extend `tests/test_api_routes.py` for updated detect → conversation (next/answer) → preview flow
  - [ ] 7.4 Add fixtures/sample DOCX to validate detection and replacement cases


