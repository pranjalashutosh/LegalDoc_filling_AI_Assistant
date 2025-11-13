## Introduction / Overview

We observed flaws in the current placeholder detection for DOCX:
- Overlapping pattern matches without precedence allow weaker patterns to override stronger ones, producing noisy/incorrect placeholders and suboptimal LLM context.
- Detection of square-bracket underscore `[_____]` is not required and introduces collisions.
- Signature blocks (e.g., `Address:` or `Email:` lines) often use Word tab leaders or borders to render visual blanks. These are not literal underscores in the DOCX text, so the current regex-based approach fails to detect them.

This PRD proposes a deterministic, arbitration-based detection pipeline with explicit pattern priority and a robust signature-line heuristic, while retaining the hybrid flow and minimal-context capture for the LLM.

Scope: DOCX only. Both body paragraphs and tables are scanned; headers/footers/footnotes remain out of scope.

## Goals
- Enforce non-overlapping matches with explicit priority so that the most specific/appropriate placeholder survives.
- Remove `bracket_underscore` detection `[_____]` per requirements.
- Detect signature-line placeholders even when the visual blank is rendered via tab leaders/borders (no literal underscores).
- Preserve existing outputs: `placeholders`, `candidates` (with context), and `groups` in the session.
- Improve detection logs to aid manual inspection of LLM context.

## User Stories
- As a user, I want the detector to pick the strongest placeholder pattern so questions are relevant and clear.
- As a user, I want address/email/phone signature lines treated as fillable fields even if there are no literal underscores.
- As a developer, I want deterministic, explainable arbitration and logs so I can debug why a match was kept or dropped.

## Functional Requirements
1) Pattern set and priorities
   - Supported patterns (ordered by specificity/priority):
     1. `dollar_underscore` (e.g., `$[__________]`) – priority 5
     2. `square_bracket` (e.g., `[Placeholder Name]`) – priority 4
     3. `double_curly` (e.g., `{{ placeholder }}`) – priority 3
     4. `single_curly` (e.g., `{ placeholder }`) – priority 2
     5. `underscore` (runs of ≥3 underscores) – priority 1
   - The `bracket_underscore` pattern (`[_____ ]`) MUST be removed.

2) One-pass collection with arbitration
   - For each paragraph (body and table cells), the detector MUST collect all raw matches across patterns without committing.
   - For each match, collect: `(start, end, length, kind, priority, original_text, captured_group_if_any, locator)`.
   - Sort candidates by: start ASC, priority DESC, length DESC.
   - Sweep once; keep a match only if it does NOT overlap any previously kept span; otherwise skip.
   - Proceed to normalization/context only for kept matches.

3) Normalization and context
   - Normalization rules remain as-is (underscore label inference from `Label:` before underscores; dollar-underscore after/before label heuristics; bracket/curly from capture group; standard `normalize_placeholder_name`).
   - Context MUST include `prev/sentence/next` with clipping (≈300/400/300 chars).
   - Each kept match MUST receive a stable `instance_id` (`t{table}-r{row}-c{cell}-p{para}-s{start}-e{end}`).

4) Signature-line heuristic (no literal underscores)
   - The detector MUST treat paragraphs that start with a known signature label and have only whitespace/tabs/leader/dots/dashes afterward as placeholders even if no underscores are present.
   - Default label allowlist: `Address`, `Email`, `E-mail`, `Phone`, `Name`, `Title` (case-insensitive; with optional colon).
   - A match is valid if the remainder is empty or consists only of `[ \t._\-—]*` (no alphanumerics).
   - Signature-line matches SHOULD be assigned kind `signature_label` with highest priority (e.g., 6) to win against overlaps.

5) Logging
   - For each kept match, log at INFO: `pattern=<kind> normalized=<key> locator=<id> original=<text> prev=<prev> sentence=<sent> next=<next>` with truncated context (≤120 chars each).
   - For each dropped match due to overlap, log at DEBUG: the conflicting spans and the reason.

6) Outputs and session shape
   - Preserve existing outputs: `placeholders` (map), `candidates` (list with context and ids), and `groups` (map from `normalized` → `[instance_ids]`).
   - False-positive filtering (`reduce_false_positives`) remains in place after arbitration.

## Non-Goals (Out of Scope)
- OCR/image inputs; header/footer/footnote detection.
- Changing API routes or response shapes.
- Auto-filling signature lines without user confirmation.

## Design Considerations (Optional)
- Arbitration is per paragraph (fast, predictable). Document-wide arbitration is unnecessary at present.
- Complexity: O(M log M) per paragraph (M = candidate matches). Paragraph lengths are typically small, so runtime impact is negligible.
- The signature heuristic intentionally favors recall for common labels; the allowlist SHOULD be configurable in code and easily extended.

## Technical Considerations (Optional)
- Implementation targets:
  - `lib/placeholder_detector.py`
    - Update `detect_placeholders_with_context` to use collect → arbitrate → process pipeline.
    - Remove `bracket_underscore` regex.
    - Add `signature_label` detection as described.
    - Keep existing normalization and context extraction helpers.
  - `tests/test_placeholder_detector.py`
    - Add cases for overlapping matches, signature-line detection without literal underscores, and removal of bracket-underscore.
- No changes to routes or replacer are required.

## Success Metrics
- Zero overlapping matches in final candidate set (verified via unit tests for pathological inputs).
- ≥95% precision for deterministic placeholders; ≥90% recall for signature-line labels across sample templates.
- No regressions in total detection runtime compared to baseline (±10%).
- Improved developer observability: logs include one INFO entry per kept match; DEBUG entries explain skips due to overlap.

## Open Questions
- Do we need to expand the signature label allowlist (e.g., `Mailing Address`, `Zip`, `Country`, `Fax`, `Website`)?
- Should we make the allowlist configurable via an environment variable or a project config? (Defaults would remain in code.)
- For paragraphs with “Label:” on one line and the visual blank on the next line, should we treat the next empty/leader-only paragraph as part of the same placeholder?


