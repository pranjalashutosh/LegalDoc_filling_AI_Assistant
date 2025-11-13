## Relevant Files

- `lib/placeholder_detector.py` - Detection engine; implement collect→arbitrate→process pipeline; remove `[_____ ]` pattern; add signature-line heuristic; keep context/logging.
- `tests/test_placeholder_detector.py` - Unit tests to validate arbitration (no overlaps), removal of bracket-underscore, and signature-line detection without literal underscores.

### Notes

- Keep API shapes intact (`placeholders`, `candidates`, `groups`) so routes remain unchanged.
- Log kept/dropped matches to aid inspection; keep existing INFO logs for kept matches.
- Priority order (high→low): `signature_label` (6), `dollar_underscore` (5), `square_bracket` (4), `double_curly` (3), `single_curly` (2), `underscore` (1).
- Arbitration per paragraph: sort by start ASC, priority DESC, length DESC; drop overlaps.

## Tasks

- [x] 1.0 Implement candidate collection and arbitration in `lib/placeholder_detector.py`
  - [x] 1.1 Define pattern priority map and ordered patterns (dollar_underscore→square_bracket→double_curly→single_curly→underscore)
  - [x] 1.2 For each paragraph/cell, collect raw matches with `(start,end,length,kind,priority,original,captured,locator)`
  - [x] 1.3 Sort candidates by start ASC, priority DESC, length DESC
  - [x] 1.4 Sweep once; keep only non-overlapping matches, skip and mark dropped when overlapping
  - [x] 1.5 Convert kept matches to normalized keys, capture context, build instance IDs
  - [x] 1.6 Populate `placeholders`, `candidates`, and `groups` from kept matches

- [x] 2.0 Remove `bracket_underscore` pattern and references
  - [x] 2.1 Delete the `[_____ ]` regex from detection functions
  - [x] 2.2 Remove any normalization/branching referencing `bracket_underscore`
  - [x] 2.3 Update comments/docs to reflect removal

- [x] 3.0 Add signature-line heuristic for Address/Email/Phone/Name/Title with leader/tabs and no underscores
  - [x] 3.1 Define case-insensitive allowlist and trailing-leader regex: remainder must be only `[ \t._\-—]*`
  - [x] 3.2 Detect paragraphs that start with label + optional colon and match leader-only remainder
  - [x] 3.3 Emit `signature_label` matches with highest priority (6) and generate normalized key from label
  - [x] 3.4 (Optional) Handle two-line cases: label on one line, leader-only next line
  - [x] 3.5 Add to candidates for arbitration alongside other matches

- [x] 4.0 Preserve normalization/context generation and enhance logging for kept/dropped matches
  - [x] 4.1 Reuse underscore/dollar/bracket/curly normalization; add path for `signature_label`
  - [x] 4.2 Use `_extract_sentence_context` for every kept match; ensure clipping bounds
  - [x] 4.3 Log INFO for kept (pattern, normalized, locator, truncated prev/sentence/next)
  - [x] 4.4 Log DEBUG for dropped overlaps with reason (conflicting span and winner)

- [x] 5.0 Update unit tests in `tests/test_placeholder_detector.py` for arbitration, signature-lines, and pattern removal
  - [x] 5.1 Overlap test: ensure higher-priority longer match wins, others dropped
  - [x] 5.2 Removal test: `[_____ ]` no longer produces matches
  - [x] 5.3 Signature-line test: `Address:` + tabs/leader-only remainder yields placeholder
  - [x] 5.4 Context/instance-id test: ensure sentence neighbors captured and stable IDs assigned
  - [x] 5.5 False-positive filter still applied after arbitration

- [ ] 6.0 Validate performance and regressions on sample DOCX templates
  - [ ] 6.1 Measure detection time on sample files; compare to baseline (±10%)
  - [ ] 6.2 Verify placeholder counts and keys are as expected (no regressions)
  - [ ] 6.3 Spot-check logs and LLM context snippets for quality
  - [ ] 6.4 Adjust priorities if needed and re-run tests


