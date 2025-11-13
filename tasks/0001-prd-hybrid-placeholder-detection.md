## Introduction / Overview

This enhancement introduces a hybrid placeholder detection system for DOCX documents. The system first performs deterministic parsing to identify likely placeholders and always invokes an LLM to validate the finding, generate clear, context-aware questions, collect user responses, and fill values back into the document. The rest of the application (preview and download flows) remains unchanged.

Primary problems solved:
- Improve precision and coverage of placeholder detection in DOCX, including ambiguous forms like blanks and check/radio indicators.
- Provide high-quality, context-aware questions that guide users to supply correct values.
- Streamline filling so users can complete documents quickly and reliably.

Scope: DOCX only.

## Goals
- Increase reliable identification of placeholders in DOCX using deterministic rules augmented by LLM validation.
- Provide clear, context-aware questions to collect required inputs from the user.
- Support checkboxes/radio-style inputs (square/circle indicators) with natural language prompts.
- Auto-fill the document immediately upon each answer; allow per-instance editing afterward.
- Keep preview and download behaviors unchanged once the document is fully filled.

## User Stories
- As a user, I want blanks and bracketed fields in a DOCX to be detected so I can quickly fill them.
- As a user, I want the system to ask clear questions about ambiguous fields so I know exactly what to provide.
- As a user, I want repeated fields like Client Name to be asked once and reused everywhere.
- As a user, I want to select options for check/radio-like fields (e.g., Male/Female) via a simple question.
- As a user, I want each answer to fill the document immediately so I can see progress as I go.

## Functional Requirements
1) Deterministic parsing (DOCX only)
   - The parser MUST scan paragraphs and tables in DOCX for the following patterns as candidate placeholders:
     - [TITLE], [title], and bracketed forms like [something written]
     - Blanks represented by ≥4 consecutive underscores (e.g., "Name: ______")
     - Patterns like $[__________]
     - Words followed by blanks (e.g., "Name:______", "Date: ______")
     - Mixed casing variants of bracketed tokens (e.g., [TITLE]/[title])
     - Square/circle indicators that imply checkboxes or radio buttons in tables or inline text
   - The parser MUST ignore the following and NOT treat them as placeholders:
     - Common acronyms (e.g., LLC, USA)
     - Section tags (e.g., [Exhibit A])
     - Citations like [1]
     - Email template boilerplate (e.g., unsubscribe blocks)
   - The parser MUST include detection inside tables. Content in headers, footers, and footnotes is out of scope for detection.

2) LLM validation and question generation
   - For every candidate placeholder detected deterministically, the system MUST invoke the LLM (Gemini 2.5 Pro Preview) to:
     - Validate whether the element is indeed a placeholder based on the sentence + immediate neighboring sentences.
     - If a placeholder, generate a concise, context-aware question in English to solicit the correct value from the user.
     - For check/radio-like indicators (e.g., Male/Female), generate a single-select question that clearly lists the options, then set the selection based on the user's answer.
   - The LLM MUST receive only the minimal necessary text: the sentence that contains the candidate and its immediate neighbors.
   - The LLM MUST operate in English only.

3) Consolidation and reuse
   - The system MUST consolidate repeated placeholders that represent the same semantic field (e.g., Client Name) into one question, and reuse the given answer across all matched instances.

4) Questioning and answering UX
   - The system MUST present questions one-by-one.
   - The system MUST NOT display auto-suggested answers; only ask and capture the user’s response.
   - Upon receiving an answer, the system MUST immediately fill all linked instances in the document.
   - If the user edits an answer later, the system MUST limit the change to the single selected instance (no global propagation).

5) Document fill and integrity
   - Filled content MUST preserve original DOCX layout, formatting, and surrounding punctuation, to the extent supported by the existing replacer.
   - Checkbox/radio selections MUST reflect the user’s responses (e.g., mark Male and unmark Female for a single-select choice).

6) Performance and cost
   - No hard limit on LLM calls per page. The system SHOULD use reasonable batching or caching where safe, but not at the expense of correctness or question quality.

7) Auditability
   - The system SHOULD maintain an in-memory list of placeholders detected, questions asked, and answers provided for the current session to support user review within the existing UI capabilities.

## Non-Goals (Out of Scope)
- OCR/image inputs are out of scope; DOCX only.
- No changes to preview and download flows beyond reflecting filled content.
- No signature workflows or e-sign integrations.
- No multilingual detection or translation.
- No telemetry/analytics beyond what the app already collects.
- Headers, footers, and footnotes detection is out of scope.

## Design Considerations (Optional)
- UX:
  - One-by-one questioning flow.
  - No suggested answers; keep prompts concise and context-aware.
  - Immediate auto-fill after each answer; per-instance edits allowed.
- Check/Radio:
  - Treat as single-select unless surrounding text clearly indicates multi-select. The LLM should generate mutually exclusive choices when phrased as radio.

## Technical Considerations (Optional)
- Integration points:
  - Deterministic detection extends the existing placeholder detection module in the codebase.
  - Filling uses the existing document replacer to write values back into the DOCX.
- Model: Gemini 2.5 Pro Preview (English only).
- Context window to LLM: sentence containing the candidate + immediate neighbor sentences.
- Consolidation: Use canonical keys derived from LLM outputs (e.g., "client_name") to map repeated placeholders to one answer.
- Ambiguity/low confidence: When the LLM indicates uncertain classification, the system SHOULD ask the user for confirmation rather than auto-filling.
- Tables: Detection MUST include table cells; headers/footers/footnotes excluded.

## Success Metrics
- ≥95% precision on deterministic placeholder candidate extraction for in-scope patterns (excluding ignored categories).
- ≥85% precision on LLM-validated placeholder classification using sentence-level context.
- Users complete a typical DOCX NDA in ≤3 minutes in the one-by-one flow.
- Question helpfulness: ≥80% of questions rated clear in internal QA (or low re-ask rate in pilot testing).

## Open Questions
- Exact representation of check/radio in DOCX may vary (content controls, special glyphs, or tables). Confirm target DOCX encoding patterns to prioritize in detection rules.
- Define the minimal confidence threshold from the LLM to auto-accept classification vs. asking the user to confirm.
- Confirm whether consolidation keys should be persisted beyond the current session for reuse across documents of the same template.


