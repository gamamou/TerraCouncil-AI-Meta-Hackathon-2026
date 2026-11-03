# RC1 code review — November 3, 2026

The developer-provided `TERRA-META-GITHUB-SOURCE-RC1.zip` was inspected before source import.

## Archive structure

- 58 Python modules under `src/`.
- Five root files: `.env.example`, `.gitignore`, `README.md`, `SECURITY.md`, `SOURCE_INVENTORY.json`.
- All 58 Python modules parsed with Python's AST parser (zero syntax errors).
- Third-party imports detected: `reportlab` and `shapely`, alongside Python standard-library and local source modules.
- Local packaging scan reported `scan_issues: []`, `large_omitted: []`. This is not a comprehensive vulnerability scan.

## Critical packaging observation

The uploaded ZIP does **not** include the current `data/science_packages/TERRA-META-DEMO-054` application's `server.py`, homepage or final policy-119 audio pipeline. They must be sourced from the developer's validated working installation, reviewed, and committed separately. No one should claim this snapshot includes the entire working Demo yet.

## Technical assessment

Strengths visible in inspected code:
- `src/council.py`: real HTTP client integration for the Meta chat-completions endpoint, explicit credentials and evidence gating.
- `src/local_council_server.py`: loopback server, consent and API-call safeguards, local trace checkpointing, no automatic retries on paid API errors.
- Multiple modules provide scientific-source selection, spatial-context checks, multi-agent deliberation, oral-script validation and PDF outputs.
- Strong distinction between candidate evidence and admitted/validated evidence in user-facing claims.

Limitations:
- No integrated live-key end-to-end tests can be performed without authorized provider accounts.
- Not all source modules are necessarily reachable from the final Demo.
- Missing private data and generated media are intentional; cloning GitHub alone should not be advertised as recreating private outputs.

## Publish gate

Commit only after checking the final source file inventory, testing imports, verifying that no credentials or private science artifacts are included, and documenting the final application's actual startup steps.
